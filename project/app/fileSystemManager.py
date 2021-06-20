import logging
import os
import re
import sys

from app.models import ImageES,Folder
from scripts.esScript import es
from app.utils import get_random_number, ImageFeature, processingLock

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
        folders, root = self.__split_uri_and_get_root__(uri)

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
                new_node = Node(folder, ids[i])
                new_node.parent = node
                node.children[folder] = node = new_node

        node.terminated = True

    # add a new folder under the given uri
    # given uri must exist in fileSystemManager
    def expand_uri(self, uri, folder, id):
        folders, root = self.__split_uri_and_get_root__(uri)

        if root in self.trees:
            node = self.trees[root]

            for i in range(1, len(folders)):
                f = folders[i]
                if f in node.children:
                    node = node.children[f]

            new_node = Node(folder, id)
            new_node.terminated = True
            node.children[folder] = new_node

    def get_last_node(self, uri):
        folders, root = self.__split_uri_and_get_root__(uri)

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
        folders, root = self.__split_uri_and_get_root__(uri)

        logging.info("[SERVER-TO-NEO]: [INFO] Creating uri: " + str(uri) + " Folders found: " + str(folders))

        if root in self.trees:
            node = self.trees[root]
            if len(folders) == 1:
                node.terminated = True
                return node
        else:
            saved_node = Folder(id_=get_random_number(), name=root, root=True,
                                terminated=True if len(folders) == 1 else False).save()
            self.trees[root] = node = Node(root, saved_node.id_)

        node = self.create_uri_in_neo4j_for_folders(folders, node)
        return node

    def create_uri_in_neo4j_for_folders(self, folders, node):
        for i in range(1, len(folders)):
            folder = folders[i]
            if folder in node.children:
                node = node.children[folder]
                if i == len(folders) - 1:
                    node.terminated = True
            else:
                saved_node = Folder(id_=get_random_number(), name=folder,
                                    terminated=True if i == len(folders) - 1 else False).save()

                parent = Folder.nodes.get(id_=node.id)
                saved_node.parent.connect(parent)

                new_node = Node(folder, saved_node.id_, saved_node.terminated)
                new_node.parent = node
                node.children[folder] = node = new_node
        return node

    def __split_uri_and_get_root__(self, uri):
        folders = re.split("[\\\/]+", uri)
        if folders[len(folders) - 1].strip() == "":
            folders = folders[:-1]

        root = folders[0]
        return folders, root

    def __buil_full_path__(self, paths):
        path = ""
        for p in paths:
            path = os.path.join(path, p)
        return path

    def delete_folder_from_fs(self, uri, frr):
        try:
            if self.exist(uri):
                folders_to_be_deleted, node = self.get_folders_to_be_deleted_from_uri(uri)

                deleted_images = self.pop_folders_from_to_be_deleted(folders_to_be_deleted, frr)

                # if parent folders have no children folders and no images, delete it
                node = self.check_for_childrens_and_delete_them(node)

                if node.name in self.trees and len(node.children) == 0:
                    self.trees.pop(node.name)

                return deleted_images
        except Exception as e:
            logging.info("[Deleting]: [ERROR] Delete error " + str(e))

    def pop_folders_from_to_be_deleted(self, folders_to_be_deleted, frr):
        deleted_images = []
        while folders_to_be_deleted != []:
            f = folders_to_be_deleted.pop()
            if not f:
                continue

            images = f.getImages()

            if images is not None:
                for image in images:
                    try:
                        frr.remove_image(image.hash)
                    except Exception as e:
                        logging.info(
                            "[Deleting]: [ERROR] Couldn't remove person thumbnail and/or person entity because: " + str(
                                e))
                    self.delete_images(deleted_images, f, image)

            children_folders = f.getChildren()
            if children_folders:
                folders_to_be_deleted.extend(list(children_folders))
            f.delete()
        return deleted_images

    def get_folders_to_be_deleted_from_uri(self, uri):
        node = self.get_last_node(uri)
        if node and node.parent:
            node.parent.delete_node(node)
        node.deleting = True
        foldersto_be_deleted = [Folder.nodes.get_or_none(id_=node.id)]
        return foldersto_be_deleted, node

    def delete_images(self, deleted_images, f, image):
        if len(image.folder) > 1:  # if image is in different folders
            current_image_uri, root = self.__split_uri_and_get_root__(image.folder_uri)
            current_image_uri = self.__buil_full_path__(current_image_uri)
            if current_image_uri == self.__full_path_for_folder_node__(f):
                for folder in image.folder:
                    if folder.id != f.id and not folder.isChildOf(f.id_):
                        image.folder_uri = self.__full_path_for_folder_node__(folder)
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
                deleted_images.append(ImageFeature(hash=image.hash))
            except Exception as e:
                logging.info("[Deleting]: [ERROR] Image missing: " + str(e))

    def check_for_childrens_and_delete_them(self, node):
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
            else:
                break
        return node

    def __full_path_for_folder_node__(self, f):
        paths = f.getFullPath()
        paths.reverse()
        paths.append(f.name)
        return self.__buil_full_path__(paths)

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
                    self.delete_cities(l)
                    l.delete()

    def delete_cities(self, l):
        for city in l.city:
            city.location.disconnect(l)
            if len(city.location) == 0:
                self.delete_regions(city)
                city.delete()

    def delete_regions(self, city):
        for region in city.region:
            region.city.disconnect(city)
            if len(region.city) == 0:
                self.delete_countries(region)
                region.delete()

    def delete_countries(self, region):
        for country in region.country:
            country.region.disconnect(region)
            if len(country.region) == 0:
                country.delete()

    def get_all_uris(self):
        uris = []

        def build_uri(current, uri):
            for folder in current.children:
                path = os.path.join(uri, folder)
                next_node = current.children[folder]
                if next_node.terminated:
                    uris.append(path)
                build_uri(next_node, path)

        for node in self.trees.keys():
            build_uri(self.trees[node], os.path.normpath(node + "/"))

        return uris
