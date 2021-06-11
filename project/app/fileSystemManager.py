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

        # if current node is the last one of an uri, it is terminated
        # ex: for uri C:\User\abcd\ef\, node 'ef' is terminated
        self.terminated = terminated

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def deleteNode(self, node):
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

        return node.terminated

    def addFullPathUri(self, uri: str, ids: list):
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
    def expandUri(self, uri, folder, id):
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

    def getLastNode(self, uri):
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

    def createUriInNeo4j(self, uri):
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

    def deleteFolderFromFs(self, uri):
        if self.exist(uri):
            node = self.getLastNode(uri)

            if node and node.parent:
                node.parent.deleteNode(node)

            folderstoBeDeleted = [Folder.nodes.get_or_none(id_=node.id)]

            deletedImages = []

            while folderstoBeDeleted != []:
                f = folderstoBeDeleted.pop()
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
                                        esImage = ImageES.get(using=es, index='image', id=image.hash)
                                        esImage.uri = image.folder_uri
                                        esImage.save(using=es)
                                        break
                        else:
                            self.deleteConnectedTagsAndPersons(image)
                            self.deleteLocations(image)
                            image.delete()

                            thumbnail = os.path.join("app", "static", "thumbnails", str(image.hash)) + ".jpg"
                            os.remove(thumbnail)

                            esImage = ImageES.get(using=es, index='image', id=image.hash)
                            esImage.delete(using=es)
                            deletedImages.append(ImageFeature(hash=image.hash))

                childrenFolders = f.getChildren()
                if childrenFolders:
                    folderstoBeDeleted.extend(list(childrenFolders))
                f.delete()

            # if parent folders have no children folders and no images, delete it
            while node.parent:
                parentFolder = Folder.nodes.get_or_none(id_=node.parent.id)
                if not parentFolder:
                    node.parent.deleteNode(node)
                    node = node.parent
                    continue
                currNode = node
                node = node.parent
                children = parentFolder.getChildren()
                if len(children) == 0 and not parentFolder.terminated:
                    parentFolder.delete()
                    if currNode.name in node.children:
                        node.children.pop(currNode.name)
                else: break

            if node.name in self.trees:
                if len(node.children) == 0:
                    self.trees.pop(node.name)

            return deletedImages


    def __fullPathForFolderNode__(self, f):
        paths = f.getFullPath()
        paths.reverse()
        paths.append(f.name)
        return self.__builFullPath__(paths)

    def deleteConnectedTagsAndPersons(self, image):
        for t in image.tag:
            t.image.disconnect(image)
            if len(t.image) == 0:
                t.delete()

        for p in image.person:
            p.image.disconnect(image)
            if len(p.image) == 0:
                p.delete()

    def deleteLocations(self, image):
        if len(image.location) != 0:
            for l in image.location:
                l.image.disconnect(image)
                if len(l.image) == 0:
                    l.delete()
                    for city in l.city:
                        city.location.disconnect(l)
                        if len(city.location) == 0:
                            city.delete()
                            for region in city.region:
                                region.city.disconnect(city)
                                if len(region.city) == 0:
                                    region.delete()
                                    for country in region.country:
                                        country.region.disconnect(region)
                                        if len(country.region) == 0:
                                            country.delete()


    def getAllUris(self):
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