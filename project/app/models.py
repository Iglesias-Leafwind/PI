# Create your features here.
import random
from elasticsearch_dsl import Document, Text, Keyword, Index
from neomodel import StructuredNode, StringProperty, StructuredRel, IntegerProperty, config, \
    DateTimeProperty, FloatProperty, RelationshipTo, RelationshipFrom, OneOrMore, ZeroOrMore, BooleanProperty, \
    ArrayProperty
from neomodel import db
from scripts.esScript import es
from scripts.pcVariables import dbsPath
config.DATABASE_URL = dbsPath

# for elastic search ↓
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


# for neo4j ↓
# relations
class WasTakenIn(StructuredRel):
    rel = 'Was taken in'
    latitude = FloatProperty()
    longitude = FloatProperty()
    altitude = FloatProperty()


class IsIn(StructuredRel):
    rel = 'Is in'


class HasA(StructuredRel):
    rel = "Has a"
    originalTagName = StringProperty()
    originalTagSource = StringProperty()
    score = FloatProperty()
    manual = BooleanProperty(default=False)


class DisplayA(StructuredRel):
    rel = 'Display a'
    coordinates = ArrayProperty()
    encodings = ArrayProperty()
    icon = StringProperty()
    confiance = FloatProperty()
    approved = BooleanProperty()


# Nodes
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

    def getPersonsName(self):
        query = "MATCH (i:ImageNeo{hash:$hash})-[r:`Display a`]->(p:Person) RETURN DISTINCT p.name"
        results, meta = db.cypher_query(query, {"hash":self.hash})
        return [row[0] for row in results]

class Tag(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    image = RelationshipFrom(ImageNeo, HasA.rel, model=HasA)

    def getTop10Tags(self):
        query = "MATCH (t:Tag)<-[r]-(i) WITH t,COUNT(r) AS rels RETURN t, rels ORDER BY rels DESC LIMIT 10"
        results, meta = db.cypher_query(query)
        return [(Tag.inflate(row[0]).name, row[1]) for row in results]

    def tagSourceStatistics(self):
        query = "MATCH (t:Tag)<-[r]-(i) WITH DISTINCT t, r.originalTagSource AS ts WITH COUNT(t) AS tags,ts RETURN ts,tags ORDER BY tags DESC"
        results, meta = db.cypher_query(query)
        return [(row[0], row[1]) for row in results]
    
    def getTags(self,tag_source):
        query = "MATCH (t:Tag)<-[r:`Has a`{originalTagSource: $tag_source}]-(i) WITH DISTINCT t.name as name RETURN left(name,1), name ORDER BY name ASC"
        results, meta = db.cypher_query(query, {"tag_source":tag_source})
        return [(row[0].upper(),row[1]) for row in results]
        
class Person(StructuredNode):
    name = StringProperty(required=True)
    image = RelationshipFrom(ImageNeo, DisplayA.rel, model=DisplayA)

    def countRelations(self):
        query = "MATCH (i:ImageNeo)-[r:`Display a`]->(p:Person) where id(p)=$id with count(r) as rels RETURN rels"
        results, meta = db.cypher_query(query, {"id": self.id})
        return [row[0] for row in results]

    def getDetails(self):
        query = "MATCH (i:ImageNeo)-[r:`Display a`]->(p:Person)  WHERE id(p)=$id RETURN r"
        results, meta = db.cypher_query(query, {"id": self.id})
        return [row[0] for row in results]

    def getVerified(self):
        query = "MATCH (p:Person)<-[r:`Display a` {approved: true}]-(i:ImageNeo)  RETURN p.name"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

    def countPerson(self):
        query = "MATCH (p:Person) WITH count(p) AS persons RETURN persons"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

    def getRIP(self, tf, page):
        size = 20
        page = max(1, page)
        query = "MATCH (i:ImageNeo)-[r:`Display a`]-(p:Person) WHERE r.approved = $tf RETURN r, i, p SKIP $skip LIMIT $limit"
        results, meta = db.cypher_query(query,{'tf': tf, 'skip': (page - 1) * size, 'limit': page * size})
        return [(DisplayA.inflate(row[0]), ImageNeo.inflate(row[1]), Person.inflate(row[2])) for row in results]

class Country(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    region = RelationshipFrom('Region', IsIn.rel, model=IsIn)

class Region(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    country = RelationshipTo('Country', IsIn.rel, model=IsIn)
    city = RelationshipFrom('City', IsIn.rel, model=IsIn)

class City(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    region = RelationshipTo('Region', IsIn.rel, model=IsIn)
    location = RelationshipFrom('Location', IsIn.rel, model=IsIn)

class Location(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    image = RelationshipFrom('ImageNeo', WasTakenIn.rel, model=WasTakenIn)
    city = RelationshipTo('City', IsIn.rel, model=IsIn)

    def countLocations(self):
        query = "MATCH(c: City), (r:Region), (cnt:Country) WITH COUNT(c) AS cs, count(r) AS rs, count(cnt) AS cnts RETURN cs + rs + cnts"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]


class Folder(StructuredNode):
    id_ = IntegerProperty(unique_index=True)
    name = StringProperty(required=True)
    root = BooleanProperty(default=False)
    terminated = BooleanProperty(default=False)
    parent = RelationshipTo("Folder", IsIn.rel, model=IsIn)
    children = RelationshipFrom("Folder", IsIn.rel, model=IsIn)
    images = RelationshipFrom("ImageNeo", IsIn.rel, model=IsIn)

    def getImages(self):
        query = "MATCH (i:ImageNeo)-[:`Is in`]->(f:Folder {id_:$id_}) RETURN i"
        results, meta = db.cypher_query(query, {"id_": self.id_})
        return [ImageNeo.inflate(row[0]) for row in results]

    def countTerminatedFolders(self):
        query = "MATCH(f:Folder)<-[]-(i:ImageNeo) WITH DISTINCT f.name AS name RETURN COUNT(name)"
        results, meta = db.cypher_query(query)
        return [row[0] for row in results]

    def getChildren(self):
        query = "MATCH (c:Folder)-[:`Is in`]->(f:Folder {id_:$id_}) RETURN c"
        results, meta = db.cypher_query(query, {"id_": self.id_})
        return [self.inflate(row[0]) for row in results]

    def isChildOf(self, folder_id):
        query = "MATCH (f:Folder{id_:$id_})-[*]->(p:Folder{id_:$folderId}) return p"
        results, meta = db.cypher_query(query, {"id_": self.id_, "folderId": folder_id})
        return len([path[0] for path in results]) != 0

    def getFullPath(self):
        query = "MATCH (f:Folder {id_:$id_})-[*]-> (c:Folder) RETURN c.name"
        results, meta = db.cypher_query(query, {"id_": self.id_})
        return [path[0] for path in results]

    def getImagesByPage(self, page): # page [1:inf[
        size = 20
        page = max(1, page)
        query = "MATCH (i:ImageNeo)-[:`Is in`]->(f:Folder {id_:$id_}) RETURN i SKIP $skip LIMIT $limit"
        results, meta = db.cypher_query(query, {"id_": self.id_, "skip": (page - 1) * size, "limit": page * size})
        return [ImageNeo.inflate(row[0]) for row in results]

