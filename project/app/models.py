## @package app
#  This module contains neo4j python class models
#
#  More details.
import random
from elasticsearch_dsl import Document, Text, Keyword, Index
from neomodel import StructuredNode, StringProperty, StructuredRel, IntegerProperty, config, \
    DateTimeProperty, FloatProperty, RelationshipTo, RelationshipFrom, OneOrMore, ZeroOrMore, BooleanProperty, \
    ArrayProperty
from neomodel import db
from scripts.esScript import es
from scripts.pcVariables import dbsPath
config.DATABASE_URL = dbsPath

## Image class format for elastic search
#
#  More details.
class ImageES(Document):
    uri = Text(required=True)
    hash = Text()
    tags = Text()

    class Index:
        name = 'image'

ImageES.init(using=es)
i = Index(using=es, name=ImageES.Index.name)
if not i.exists(using=es):
    i.create()


## Relation class format for neo4j
# between locations,cities,regions and countries
#  More details.
class WasTakenIn(StructuredRel):
    rel = 'Was taken in'
    latitude = FloatProperty()
    longitude = FloatProperty()
    altitude = FloatProperty()

## Relation class format for neo4j
# between Images and folders and folders
#  More details.
class IsIn(StructuredRel):
    rel = 'Is in'

## Relation class format for neo4j
# between Images and tags
#  More details.
class HasA(StructuredRel):
    rel = "Has a"
    originalTagName = StringProperty()
    originalTagSource = StringProperty()
    score = FloatProperty()
    manual = BooleanProperty(default=False)

## Relation class format for neo4j
# between people and Image
#  More details.
class DisplayA(StructuredRel):
    rel = 'Display a'
    coordinates = ArrayProperty()
    encodings = ArrayProperty()
    icon = StringProperty()
    confiance = FloatProperty()
    approved = BooleanProperty()


## Object Image class format for neo4j
# containing:
#   folder path
#   image name
#   creation date
#   insertion date
#   processing data
#   image format
#   image width
#   image height
#   image hash
#   It has relations between tags
#   It has relations between person
#   It has relations between locations
#   It has relations between folders
#  More details.
class ImageNeo(StructuredNode):
    folder_uri = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    creation_date = StringProperty()
    insertion_date = DateTimeProperty(default_now=True)
    processing = StringProperty()
    format = StringProperty()
    width = IntegerProperty()
    height = IntegerProperty()
    hash = StringProperty(index=True)
    tag = RelationshipTo("Tag", HasA.rel, model=HasA)
    person = RelationshipTo("Person", DisplayA.rel, model=DisplayA)
    location = RelationshipTo("Location", WasTakenIn.rel, model=WasTakenIn)
    folder = RelationshipTo("Folder", IsIn.rel, model=IsIn)

    ## Extract all persons from current image
    #   @rtype Array of strings
    #   @return Returns all persons name that are in an image
    #  More details.
    def getPersonsName(self):
        query = "MATCH (i:ImageNeo{hash:$hash})-[r:`Display a`]->(p:Person) RETURN DISTINCT p.name"
        results, meta = db.cypher_query(query, {"hash":self.hash})
        return [row[0] for row in results]
## Object Tag class format for neo4j
# containing:
#   tag name
#   It has relations with Image
#  More details.
class Tag(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    image = RelationshipFrom(ImageNeo, HasA.rel, model=HasA)

    ## Gets top 10 most common tags
    #   @rtype array of tuples (Tag class object, integer)
    #   @return Returns A tag class and the quantity of relations that that tag has
    #  More details.
    def getTop10Tags(self):
        query = "MATCH (t:Tag)<-[r]-(i) WITH t,COUNT(r) AS rels RETURN t, rels ORDER BY rels DESC LIMIT 10"
        results, meta = db.cypher_query(query)
        return [(Tag.inflate(row[0]).name, row[1]) for row in results]

    ## Extract tag source for statistics
    #   @rtype Array of tuples of (string,integer)
    #   @return returns a tuple of every source available ordered by quantity
    #  More details.
    def tagSourceStatistics(self):
        query = "MATCH (t:Tag)<-[r]-(i) WITH DISTINCT t, r.originalTagSource AS ts WITH COUNT(t) AS tags,ts RETURN ts,tags ORDER BY tags DESC"
        results, meta = db.cypher_query(query)
        return [(row[0], row[1]) for row in results]

    ## Gets all tags of a specific source
    #   @param tag_source String with the name of the tag source
    #   @rtype array of tuples of (string, string)
    #   @return Returns all tags of a specific source ordered by initial letter (A,B,C,D,E,F,G) 1st string of the tuple is the letter 2nd string of the tuple is the tag name
    #  More details.
    def getTags(self,tag_source):
        query = "MATCH (t:Tag)<-[r:`Has a`{originalTagSource: $tag_source}]-(i) WITH DISTINCT t.name as name RETURN left(name,1), name ORDER BY name ASC"
        results, meta = db.cypher_query(query, {"tag_source":tag_source})
        return [(row[0].upper(),row[1]) for row in results]
## Object Person class format for neo4j
# containing:
#   person name
#   It has relations with Image
#  More details.
class Person(StructuredNode):
    name = StringProperty(required=True)
    image = RelationshipFrom(ImageNeo, DisplayA.rel, model=DisplayA)

    ## Counts how many relations a person has with images
    #   @rtype Array of integer
    #   @return Returns a single integer inside an array
    #  More details.
    def countRelations(self):
        query = "MATCH (i:ImageNeo)-[r:`Display a`]->(p:Person) where id(p)=$id with count(r) as rels RETURN rels"
        results, meta = db.cypher_query(query, {"id": self.id})
        return [row[0] for row in results]

    ## Extract all person details
    #   @rtype DisplayA class
    #   @return Returns the relation class that contains all of the person details
    #  More details.
    def getDetails(self):
        query = "MATCH (i:ImageNeo)-[r:`Display a`]->(p:Person)  WHERE id(p)=$id RETURN r"
        results, meta = db.cypher_query(query, {"id": self.id})
        return [row[0] for row in results]

    ## Gets every person that is verified
    #   @rtype Array of strings
    #   @return Returns all persons name that are verified
    #  More details.
    def getVerified(self):
        query = "MATCH (p:Person)<-[r:`Display a` {approved: true}]-(i:ImageNeo)  RETURN p.name"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

    ## Count the number of persons that exist in neo4j database
    #   @rtype Array of integer
    #   @return Returns an array of a single integer
    #  More details.
    def countPerson(self):
        query = "MATCH (p:Person) WITH count(p) AS persons RETURN persons"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

    ## RIP Relation Image Person
    #   @rtype Array of tuples (DisplayA class, ImageNeo class, Person class)
    #   @return Returns an array of tuples of 3 classes that are needed to show image on frontend
    #  More details.
    def getRIP(self, tf):
        query = "MATCH (i:ImageNeo)-[r:`Display a`]-(p:Person) WHERE r.approved = $tf RETURN r, i, p"
        results, meta = db.cypher_query(query,{'tf': tf})
        return [(DisplayA.inflate(row[0]), ImageNeo.inflate(row[1]), Person.inflate(row[2])) for row in results]
## Object Country class format for neo4j
# containing:
#   country name
#   It has relations with region
#  More details.
class Country(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    region = RelationshipFrom('Region', IsIn.rel, model=IsIn)
## Object Region class format for neo4j
# containing:
#   region name
#   It has relations with city
#  More details.
class Region(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    country = RelationshipTo('Country', IsIn.rel, model=IsIn)
    city = RelationshipFrom('City', IsIn.rel, model=IsIn)
## Object City class format for neo4j
# containing:
#   city name
#   It has relations with region
#   It has relations with location
#  More details.
class City(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    region = RelationshipTo('Region', IsIn.rel, model=IsIn)
    location = RelationshipFrom('Location', IsIn.rel, model=IsIn)
## Object Location class format for neo4j
# containing:
#   location name
#   It has relations with city
#   It has relations with image
#  More details.
class Location(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    image = RelationshipFrom('ImageNeo', WasTakenIn.rel, model=WasTakenIn)
    city = RelationshipTo('City', IsIn.rel, model=IsIn)

    ## Count the number of locations that exist
    #   @rtype Array of integers
    #   @return Returns an array of a single integer
    #  More details.
    def countLocations(self):
        query = "MATCH(c: City), (r:Region), (cnt:Country) WITH COUNT(c) AS cs, count(r) AS rs, count(cnt) AS cnts RETURN cs + rs + cnts"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

## Object Folder class format for neo4j
# containing:
#   folder id_
#   folder name
#   if it is root or not
#   if it is terminated and there is no more folders bellow
#   It has relations with Folder its parent
#   It has relations with Folder its children
#   It has relations with Images
#  More details.
class Folder(StructuredNode):
    id_ = IntegerProperty(unique_index=True)
    name = StringProperty(required=True)
    root = BooleanProperty(default=False)
    terminated = BooleanProperty(default=False)
    parent = RelationshipTo("Folder", IsIn.rel, model=IsIn)
    children = RelationshipFrom("Folder", IsIn.rel, model=IsIn)
    images = RelationshipFrom("ImageNeo", IsIn.rel, model=IsIn)

    ## Get all images of a folder
    #   @rtype Array of ImageNeo class
    #   @return Returns all images that that folder contains
    #  More details.
    def getImages(self):
        query = "MATCH (i:ImageNeo)-[:`Is in`]->(f:Folder {id_:$id_}) RETURN i"
        results, meta = db.cypher_query(query, {"id_": self.id_})
        return [ImageNeo.inflate(row[0]) for row in results]

    ## Counts how many terminated folder exist
    #   @rtype Array of integers
    #   @return Returns an array of a single integer
    #  More details.
    def countTerminatedFolders(self):
        query = "MATCH(f:Folder)<-[]-(i:ImageNeo) WITH DISTINCT f.name AS name RETURN COUNT(name)"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

    ## gets all children of the current folder
    #   @rtype Array of Folder class
    #   @return Returns children of the current folder
    #  More details.
    def getChildren(self):
        query = "MATCH (c:Folder)-[:`Is in`]->(f:Folder {id_:$id_}) RETURN c"
        results, meta = db.cypher_query(query, {"id_": self.id_})
        return [self.inflate(row[0]) for row in results]

    ## check if a folder is child of another folder
    #   @param folder_id Is the folder id that will be checked if it is the child of the current folder
    #   @rtype Boolean
    #   @return Returns True if it is a child and False if it isn't
    #  More details.
    def isChildOf(self, folder_id):
        query = "MATCH (f:Folder{id_:$id_})-[*]->(p:Folder{id_:$folderId}) return p"
        results, meta = db.cypher_query(query, {"id_": self.id_, "folderId": folder_id})
        return len([path[0] for path in results]) != 0

    ## Gets current folder full path
    #   @rtype Array of strings
    #   @return Returns an array from the folder start until the end making a full path
    #  More details.
    def getFullPath(self):
        query = "MATCH (f:Folder {id_:$id_})-[*]-> (c:Folder) RETURN c.name"
        results, meta = db.cypher_query(query, {"id_": self.id_})
        return [path[0] for path in results]

    ## Gets images by page from folder used for lazy loading
    #   @param page is the page this number can be from 1 to infinity
    #   @rtype Array of ImageNeo class
    #   @return Returns all images of a certain page
    #  More details.
    def getImagesByPage(self, page): # page [1:inf[
        size = 20
        page = max(1, page)
        query = "MATCH (i:ImageNeo)-[:`Is in`]->(f:Folder {id_:$id_}) RETURN i SKIP $skip LIMIT $limit"
        results, meta = db.cypher_query(query, {"id_": self.id_, "skip": (page - 1) * size, "limit": page * size})
        return [ImageNeo.inflate(row[0]) for row in results]

