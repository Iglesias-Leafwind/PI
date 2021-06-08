from django import forms
from string import Template

from django.forms import CheckboxInput, HiddenInput
from django.utils.safestring import mark_safe
from neomodel import match
from neomodel.match import Traversal
# from neomodel import Traversal
from app.utils import showDict
import app.models
from app.models import Person, DisplayA, ImageNeo

from app.models import Person


class PictureWidget(forms.widgets.Widget):
    def render(self, name, value, attrs=None, **kwargs):
        html = Template("""<img src="$link"/>""")
        return mark_safe(html.substitute(link=value))


class SearchForm(forms.Form):
    query = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Search for an image...'}), max_length=100, required=False)


class SearchForImageForm(forms.Form):
    image = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Insert image path.'}), required=False)


class EditFoldersForm(forms.Form):
    path = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Insert new source folder.'}), label=" ", required=False)

class PeopleFilterForm(forms.Form):
    unverified = forms.BooleanField(required=False, label='Show Unverified', initial=showDict['unverified'], widget= CheckboxInput(
        attrs= {'class' : 'form-check-input',
                'onclick':'this.form.submit();'}
    ))
    verified = forms.BooleanField(required=False, label='Show Verified', initial=showDict['verified'], widget= CheckboxInput(
        attrs= {'class' : 'form-check-input',
                'onclick':'this.form.submit();'}
    ))

class PersonsForm(forms.Form):
    def removeRepeated(self, listt, cond):
        sett = set()
        neww = []

        for l in listt:
            if cond(l) in sett:
                continue
            neww.append(l)
            sett.add(cond(l))

        return neww

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #people = Person.nodes.all()
        image = ImageNeo.nodes.all()

        people = [ (p, i) for i in image for p in i.person.all() ]
        people = self.removeRepeated(people, lambda x : x[0].name + '-' + x[1].name)
            #print(p[0].name , '-', p[1].name)

        print('people' , len(people))
        print('showDict', showDict)
        all_rels = []
        if showDict['unverified']:
            all_rels += [ ( pp, p, i ) for (p, i) in people for pp in p.image.all_relationships(i) if not pp.approved]

            #all_rels += [ (pp, person, img) for person in people for img in person.image.all() for pp in person.image.all_relationships(img) if not pp.approved ]
            # all_rels += [ (person.image.all_relationships(img), person, img) for person in people for img in person.image.all() if not person.image.relationship(img).approved]
        if showDict['verified']:
            all_rels += [ ( pp, p, i ) for (p, i) in people for pp in p.image.all_relationships(i) if pp.approved]

            # all_rels += [ (person.image.all_relationships(img), person, img) for person in people for img in person.image.all() if person.image.relationship(img).approved]
            #all_rels += [ (pp, person, img) for person in people for img in person.image.all() for pp in person.image.all_relationships(img) if pp.approved ]
        # all_rels = [ (p, a2, a3) for (a1, a2, a3) in all_rels for p in a1]
        """
        iconss = set()
        neww = []
        for r in all_rels:
            if r[0].icon in iconss:
                continue
            iconss.add(r[0].icon)
            neww.append(r)
        all_rels = neww
        """
        print(len(all_rels))
        for index, rel in enumerate(all_rels):
            field_name = 'person_name_%s' % (index,)
            field_image = 'person_image_%s' % (index,)
            field_verified = 'person_verified_%s' % (index,)
            field_person_before = 'person_before_%s' % (index,)
            field_image_id = 'person_image_id_%s' % (index,)

            self.fields[field_image] = forms.ImageField(required=False, widget=PictureWidget)
            self.fields[field_name] = forms.CharField(required=False)
            self.fields[field_verified] = forms.BooleanField(required=False, widget=CheckboxInput(
                attrs={
                    'data-toggle': 'toggle',
                    'data-on': 'Verified',
                    'data-off': 'Unverified',
                    'data-onstyle' : 'primary',
                    'data-offstyle': 'danger'
                }
            ))
            self.fields[field_person_before] = forms.CharField(widget=HiddenInput)
            self.fields[field_image_id] = forms.CharField(widget=HiddenInput)
            # data-toggle="toggle" data-on="Verified" data-off="Unverified" data-onstyle="success" data-offstyle="danger"

            self.initial[field_image] = rel[0].icon
            self.initial[field_name] = rel[1].name # + ' -- ' + str(rel[0].confiance)
            self.initial[field_person_before] = rel[1].name
            self.initial[field_image_id] = rel[2].hash
            self.initial[field_verified] = rel[0].approved
            # self.initial[field_verified] = True if rel[0].confiance > 0.5 else False



    def get_interest_fields(self):
        for field_name in self.fields:
            if field_name.startswith('person_'):
                #number = field_name.split['_'][-1]
                # if self[field_name]
                yield self[field_name]

class FilterSearchForm(forms.Form):
    automatic = forms.BooleanField(required=False, label='Objects detected')
    manual = forms.BooleanField(required=False, label='Manual tags')
    folder_name = forms.BooleanField(required=False, label='Folder name')
    people = forms.BooleanField(required=False, label='People identified')
    text = forms.BooleanField(required=False, label='Text detected')
    exif = forms.BooleanField(required=False, label='Image metadata')
    places = forms.BooleanField(required=False, label='Scenes detected')
    breeds = forms.BooleanField(required=False, label='Pet breeds identified')
    current_url = forms.CharField(required=True, widget=HiddenInput)

class EditTagForm(forms.Form):
    tagsForm = forms.CharField(widget=forms.Textarea)
