from django.test import TestCase
from app.models import ImageNeo
from app.fileSystemManager import SimpleFileSystemManager
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
filesistem = SimpleFileSystemManager()
class FSTestCase(TestCase):

    def setUp(self):
        print("starting")
        filesistem.addFullPathUri(dir_path,[0,1,2,3,4,5,6,7])
    def test_exists(self):
        self.assertTrue(filesistem.exist(dir_path))
    def test_expand(self):
        filesistem.expandUri(dir_path,"expanding",8)
        self.assertTrue(filesistem.exist(dir_path+"\\expanding"))
    def test_delete(self):
        filesistem.deleteFolderFromFs(dir_path+"\\expanding")
        self.assertFalse(filesistem.exist(dir_path+"\\expanding"))

"""
def getLastNode(self, uri):
        folders, root = self.splitUriAndGetRoot(uri)

        if root in self.trees:
            node = self.trees[root]

            for i in range(1, len(folders)):
                folder = folders[i]
                if folder in node.children:
                    node = node.children[folder]
                else:
                    return None

            return node

def splitUriAndGetRoot(self, uri):
        folders = re.split("[\\\/]+", uri)
        if folders[len(folders) - 1].strip() == "":
            folders = folders[:-1]

        root = folders[0]
        return folders, root

def fullPathForFolderNode(self, f):
        paths = f.getFullPath()
        paths = set(paths)
        paths.add(f.name)
        return paths

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
            buildUri(self.trees[node], node)

        return uris
"""