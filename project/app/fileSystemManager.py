import os
import re
import sys

from app.models import *
from app.utils import getRandomNumber, ImageFeature, lock


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
        lock.acquire()

        if root in self.trees:
            node = self.trees[root]
        else:
            savedNode = Folder(id_=getRandomNumber(), name=root, root=True,
                               terminated=True if len(folders) == 1 else False).save()
            self.trees[root] = node = Node(root, savedNode.id_)

        for i in range(1, len(folders)):
            folder = folders[i]
            if folder in node.children:
                node = node.children[folder]
            else:
                savedNode = Folder(id_=getRandomNumber(), name=folder,
                                   terminated=True if i == len(folders) - 1 else False).save()
                parent = Folder.nodes.get(id_=node.id)
                savedNode.parent.connect(parent)

                newNode = Node(folder, savedNode.id_, savedNode.terminated)
                newNode.parent = node
                node.children[folder] = node = newNode

        lock.release()

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

            if node.parent:
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
                        self.disconnectImageRelations(image, image.tag)
                        self.disconnectImageRelations(image, image.person)
                        self.disconnectImageLocations(image)

                        if len(image.folder) > 1:
                            image.folder.disconnect(f)
                            currentImageUri, root = self.__splitUriAndGetRoot__(image.folder_uri)
                            currentImageUri = self.__builFullPath__(currentImageUri)
                            if currentImageUri == self.__fullPathForFolderNode__(f):
                                for folder in image.folder:
                                    if folder.id != f.id:
                                        image.folder_uri = self.__fullPathForFolderNode__(folder)
                                        break
                        else:
                            image.delete()
                            thumbnail = os.path.join("app", "static", "thumbnails", str(image.hash)) + ".jpg"
                            os.remove(thumbnail)

                            get = ImageES.get(using=es, index='image', id=image.hash)
                            get.delete(using=es)
                            deletedImages.append(ImageFeature(hash=image.hash))

                childrenFolders = f.getChildren()
                if childrenFolders:
                    folderstoBeDeleted.extend(list(childrenFolders))
                f.delete()

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

    def disconnectImageRelations(self, image, relations):
        for rel in relations:
            if len(rel.image) > 1:
                if isinstance(rel, Person):
                    image.person.disconnect(rel)
                else:
                    image.tag.disconnect(rel)
            else:
                rel.delete()

    def disconnectImageLocations(self, image):
        if len(image.location) != 0:
            l = image.location[0]
            if len(l.image) > 1:
                image.location.disconnect(l)
                return

            cy = l.city[0]

            if len(cy.location) > 1:
                l.delete()
                return

            ct = cy.country[0]

            if len(ct.city) == 1:
                ct.delete()

            cy.delete()
            l.delete()

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