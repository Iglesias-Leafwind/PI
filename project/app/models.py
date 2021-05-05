# Create your features here.
from elasticsearch_dsl import Document, Text, Keyword
from neomodel import StructuredNode, StringProperty, StructuredRel, IntegerProperty, config, \
    DateTimeProperty, FloatProperty, RelationshipTo, RelationshipFrom, OneOrMore, ZeroOrMore
# from manage import es
from manage import es

# config.DATABASE_URL = 'bolt://neo4j:s3cr3t@192.168.56.101:7687'
config.DATABASE_URL = 'bolt://neo4j:password@localhost:7687'


# for elastic search ↓
class ImageES(Document):
    uri = Text(required=True)
    persons = Text()
    locations = Text()
    tags = Keyword()

    class Index:
        name = 'image'


ImageES.init(using=es)


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


class DisplayA(StructuredRel):
    rel = 'Display a'
    coordinates = FloatProperty()


# Nodes
class ImageNeo(StructuredNode):
    folder_uri = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    creation_date = DateTimeProperty(default_now=False)
    insertion_date = DateTimeProperty(default_now=True)
    processing = StringProperty()
    format = StringProperty()
    width = IntegerProperty()
    height = IntegerProperty()
    tag = RelationshipTo("Tag", HasA.rel, model=HasA, cardinality=OneOrMore)
    person = RelationshipTo("Person", DisplayA.rel, model=DisplayA, cardinality=ZeroOrMore)
    location = RelationshipTo("Location", WasTakenIn.rel, model=WasTakenIn)

class Tag(StructuredNode):
    name = StringProperty(unique_index=True, required=True)
    quantity = IntegerProperty(default=1)
    image = RelationshipFrom(ImageNeo, HasA.rel, model=HasA, cardinality=OneOrMore)


class Person(StructuredNode):
    name = StringProperty(required=True)
    image = RelationshipFrom(ImageNeo, DisplayA.rel, model=DisplayA, cardinality=OneOrMore)


class Country(StructuredNode):
    name = StringProperty(unique_index=True)
    city = RelationshipFrom('City', IsIn.rel, model=IsIn)


class City(StructuredNode):
    name = StringProperty(unique_index=True)
    country = RelationshipTo(Country, IsIn.rel, model=IsIn)
    location = RelationshipFrom('Location', IsIn.rel, model=IsIn)

class Location(StructuredNode):
    name = StringProperty(unique_index=True)
    image = RelationshipFrom(ImageNeo, WasTakenIn.rel, model=WasTakenIn)
    city = RelationshipTo(City, IsIn.rel, model=IsIn)

