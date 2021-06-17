import logging
import os
import re
import sys

from app.models import *
from scripts.esScript import es
from app.utils import getRandomNumber, ImageFeature, processingLock

class Node:
    def __init__(self, name: str, id: int, terminated=False):
        self.name = name  # folder name
        self.children = {}  # key: folder name, value: node
        self.parent = None
        self.id = id

        self.deleting = False

        # if current node is the last one of an uri, it is terminated
        # ex: for uri C:\User\abcd\ef\, node 'ef' is terminated
        self.terminated = terminated

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def delete_node(self, node):
        if node.name in self.children:
            self.children.pop(node.name)

class SimpleFileSystemManager:
    def __init__(self):
        self.trees = {}  # key: folder name, value: node.

    def exist(self, uri: str):
        folders, root = self.__splitUriAndGetRoot__(uri)

        if root in self.trees:
            node = self.trees[root]
            for i in range(1, len(folders)):
                folder = folders[i].strip()
                if folder == "":
                    continue

                if folder in node.children:
                    node = node.children[folder]
                else:
                    return False
        else:
            return False

        return node.terminated ^ node.deleting

    def add_full_path_uri(self, uri: str, ids: list):
        folders = re.split("[\\\/]+", uri)
        if folders[len(folders) - 1].strip() == "":
            folders = folders[:-1]

        if len(folders) != len(ids): return

        if self.exist(uri): return

        root = folders[0]

        if root in self.trees:
            node = self.trees[root]
        else:
            self.trees[root] = node = Node(root, ids[0])

        for i in range(1, len(folders)):
            folder = folders[i]

            if folder in node.children:
                node = node.children[folder]
            else:
                newNode = Node(folder, ids[i])
                newNode.parent = node
                node.children[folder] = node = newNode

        node.terminated = True

    # add a new folder under the given uri
    # given uri must exist in fileSystemManager
    def expand_uri(self, uri, folder, id):
        folders, root = self.__splitUriAndGetRoot__(uri)

        if root in self.trees:
            node = self.trees[root]

            for i in range(1, len(folders)):
                f = folders[i]
                if f in node.children:
                    node = node.children[f]

            newNode = Node(folder, id)
            newNode.terminated = True
            node.children[folder] = newNode

    def get_last_node(self, uri):
        folders, root = self.__splitUriAndGetRoot__(uri)

        if root in self.trees:
            node = self.trees[root]

            for i in range(1, len(folders)):
                folder = folders[i]
                if folder in node.children:
                    node = node.children[folder]
                else:
                    return None

            return node

    def create_uri_in_neo4j(self, uri):
        folders, root = self.__splitUriAndGetRoot__(uri)
        print(" uri ", uri, "folders", folders)
        if root in self.trees:
            node = self.trees[root]
            if len(folders) == 1:
                node.terminated = True
                return node
        else:
            savedNode = Folder(id_=getRandomNumber(), name=root, root=True,
                               terminated=True if len(folders) == 1 else False).save()
            self.trees[root] = node = Node(root, savedNode.id_)

        for i in range(1, len(folders)):
            folder = folders[i]
            if folder in node.children:
                node = node.children[folder]
                if i == len(folders) - 1:
                    node.terminated = True
            else:
                savedNode = Folder(id_=getRandomNumber(), name=folder,
                                   terminated=True if i == len(folders) - 1 else False).save()

                parent = Folder.nodes.get(id_=node.id)
                savedNode.parent.connect(parent)

                newNode = Node(folder, savedNode.id_, savedNode.terminated)
                newNode.parent = node
                node.children[folder] = node = newNode
        return node

    def __splitUriAndGetRoot__(self, uri):
        folders = re.split("[\\\/]+", uri)
        if folders[len(folders) - 1].strip() == "":
            folders = folders[:-1]

        root = folders[0]
        return folders, root

    def __builFullPath__(self, paths):
        path = ""
        for p in paths:
            path = os.path.join(path, p)
        return path

    def delete_folder_from_fs(self, uri):
        try:
            if self.exist(uri):
                node = self.get_last_node(uri)

                if node and node.parent:
                    node.parent.delete_node(node)

                node.deleting = True

                foldersto_be_deleted = [Folder.nodes.get_or_none(id_=node.id)]

                deletedImages = []

                while foldersto_be_deleted != []:
                    f = foldersto_be_deleted.pop()
                    if not f:
                        continue

                    images = f.getImages()

                    if images is not None:
                        for image in images:
                            if len(image.folder) > 1: # if image is in different folders
                                currentImageUri, root = self.__splitUriAndGetRoot__(image.folder_uri)
                                currentImageUri = self.__builFullPath__(currentImageUri)
                                if currentImageUri == self.__fullPathForFolderNode__(f):
                                    for folder in image.folder:
                                        if folder.id != f.id and not folder.isChildOf(f.id_):
                                            image.folder_uri = self.__fullPathForFolderNode__(folder)
                                            image.save()
                                            es_image = ImageES.get(using=es, index='image', id=image.hash)
                                            es_image.uri = image.folder_uri
                                            es_image.save(using=es)
                                            break
                            else:
                                self.delete_connected_tags_and_persons(image)
                                self.delete_locations(image)
                                image.delete()

                                try:
                                    thumbnail = os.path.join("app", "static", "thumbnails", str(image.hash)) + ".jpg"
                                    os.remove(thumbnail)

                                    es_image = ImageES.get(using=es, index='image', id=image.hash)
                                    es_image.delete(using=es)
                                    deletedImages.append(ImageFeature(hash=image.hash))
                                except Exception as e:
                                    logging.info("[Deleting]: [ERROR] Image missing: ")
                                    print(e)


                    childrenFolders = f.getChildren()
                    if childrenFolders:
                        foldersto_be_deleted.extend(list(childrenFolders))
                    f.delete()

                # if parent folders have no children folders and no images, delete it
                while node.parent:
                    parent_folder = Folder.nodes.get_or_none(id_=node.parent.id)
                    if not parent_folder:
                        node.parent.delete_node(node)
                        node = node.parent
                        continue
                    curr_node = node
                    node = node.parent
                    children = parent_folder.getChildren()
                    if len(children) == 0 and not parent_folder.terminated:
                        parent_folder.delete()
                        if curr_node.name in node.children:
                            node.children.pop(curr_node.name)
                    else: break

                if node.name in self.trees and len(node.children) == 0:
                    self.trees.pop(node.name)

                return deletedImages
        except Exception as e:
            logging.info("[Deleting]: [ERROR] Delete error ")
            print(e)



    def __fullPathForFolderNode__(self, f):
        paths = f.getFullPath()
        paths.reverse()
        paths.append(f.name)
        return self.__builFullPath__(paths)

    def delete_connected_tags_and_persons(self, image):
        if len(image.tag) != 0:
            for t in image.tag:
                t.image.disconnect(image)
                if len(t.image) == 0:
                    t.delete()

        if len(image.person) != 0:
            for p in image.person:
                p.image.disconnect(image)
                if len(p.image) == 0:
                    p.delete()

    def delete_locations(self, image):
        if len(image.location) != 0:
            for l in image.location:
                l.image.disconnect(image)
                if len(l.image) == 0:
                    for city in l.city:
                        city.location.disconnect(l)
                        if len(city.location) == 0:
                            for region in city.region:
                                region.city.disconnect(city)
                                if len(region.city) == 0:
                                    for country in region.country:
                                        country.region.disconnect(region)
                                        if len(country.region) == 0:
                                            country.delete()
                                    region.delete()
                            city.delete()
                    l.delete()


    def get_all_uris(self):
        uris = []

        def buildUri(current, uri):
            for folder in current.children:
                path = os.path.join(uri, folder)
                nextNode = current.children[folder]
                if nextNode.terminated:
                    uris.append(path)
                buildUri(nextNode, path)

        for node in self.trees.keys():
            buildUri(self.trees[node], os.path.normpath(node + "/"))

        return uris