from django.test import TestCase
from app.fileSystemManager import SimpleFileSystemManager
import os
import re

dir_path = os.path.dirname(os.path.realpath(__file__))
filesistem = SimpleFileSystemManager()

class FSTestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing File System Manager")
        filesistem.addFullPathUri(dir_path, range(len(re.split("[\\\/]+", dir_path))))
    def test_exists(self):
        self.assertTrue(filesistem.exist(dir_path))
    def test_expand(self):
        filesistem.expandUri(dir_path,"expanding",8)
        self.assertTrue(filesistem.exist(dir_path+"/expanding"))
    def test_get_lastN(self):
        node = filesistem.getLastNode(dir_path)
        self.assertEquals(str(node), "tests")
    def test_get_splitgetroot(self):
        folders, root = filesistem.splitUriAndGetRoot(dir_path)
        self.assertTrue(folders)
        self.assertTrue(root in folders)
    def test_get_all(self):
        uris = filesistem.getAllUris()
        self.assertTrue(uris)