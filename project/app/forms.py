from django import forms
from string import Template

from django.forms import CheckboxInput, HiddenInput
from django.utils.safestring import mark_safe
from neomodel import match
from neomodel.match import Traversal
from neomodel import Traversal
from app.utils import showDict
from scripts.esScript import es
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
        image = ImageNeo.nodes.all()

        people = [ (p, i) for i in image for p in i.person.all() ]
        people = self.removeRepeated(people, lambda x : x[0].name + '-' + x[1].name)

        all_rels = []
        if showDict['unverified']:
            all_rels += [ ( pp, p, i ) for (p, i) in people for pp in p.image.all_relationships(i) if not pp.approved]

        if showDict['verified']:
            all_rels += [ ( pp, p, i ) for (p, i) in people for pp in p.image.all_relationships(i) if pp.approved]

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

            self.initial[field_image] = rel[0].icon
            self.initial[field_name] = rel[1].name
            self.initial[field_person_before] = rel[1].name
            self.initial[field_image_id] = rel[2].hash
            self.initial[field_verified] = rel[0].approved



    def get_interest_fields(self):
        for field_name in self.fields:
            if field_name.startswith('person_'):
                yield self[field_name]

class FilterSearchForm(forms.Form):
    automatic = forms.BooleanField(required=False, label='Objects detected', label_suffix='')
    manual = forms.BooleanField(required=False, label='Manual tags', label_suffix='')
    folder_name = forms.BooleanField(required=False, label='Folder name', label_suffix='')
    people = forms.BooleanField(required=False, label='People identified', label_suffix='')
    text = forms.BooleanField(required=False, label='Text detected', label_suffix='')
    exif = forms.BooleanField(required=False, label='Image metadata', label_suffix='')
    places = forms.BooleanField(required=False, label='Scenes detected', label_suffix='')
    breeds = forms.BooleanField(required=False, label='Pet breeds identified', label_suffix='')
    current_url = forms.CharField(required=True, widget=HiddenInput)

    objects_range_min = forms.IntegerField(min_value=0, max_value=100, required=False, label='Min confiance object extraction')
    objects_range_max = forms.IntegerField(min_value=0, max_value=100, required=False, label='Max confiance object extraction')

    places_range_min = forms.IntegerField(min_value=0, max_value=100, required=False, label='Min confiance places extraction')
    places_range_max = forms.IntegerField(min_value=0, max_value=100, required=False, label='Max confiance places extraction')

    people_range_min = forms.IntegerField(min_value=0, max_value=100, required=False, label='Min confiance people identified')
    people_range_max = forms.IntegerField(min_value=0, max_value=100, required=False, label='Max confiance people identified')

    breeds_range_min = forms.IntegerField(min_value=0, max_value=100, required=False, label='Min confiance pet breeds identified')
    breeds_range_max = forms.IntegerField(min_value=0, max_value=100, required=False, label='Max confiance pet breeds identified')

    insertion_date_activate = forms.BooleanField(required=False, label='Insertion date', label_suffix='')
    insertion_date_from = forms.CharField(max_length=10, required=False, widget=forms.TextInput
    (attrs={'id' : 'insertion_date_from', 'name' : 'insertion_date_from' }) )
    insertion_date_to = forms.CharField(max_length=10, required=False, widget=forms.TextInput
    (attrs={ 'id': 'insertion_date_to', 'name': 'insertion_date_to' }) )

    taken_date_activate = forms.BooleanField(required=False, label='Taken date', label_suffix='')
    taken_date_from = forms.CharField(max_length=10, required=False, widget=forms.TextInput
    (attrs={'id' : 'taken_date_from', 'name' : 'taken_date_from' }) )
    taken_date_to = forms.CharField(max_length=10, required=False, widget=forms.TextInput
    (attrs={ 'id': 'taken_date_to', 'name': 'taken_date_to' }) )

    size_large = forms.BooleanField(required=False, label='Large', label_suffix='')
    size_medium = forms.BooleanField(required=False, label='Medium', label_suffix='')
    size_small = forms.BooleanField(required=False, label='Small', label_suffix='')


"""
<label for="from">From</label>
<input type="text" id="from" name="from">
<label for="to">to</label>
<input type="text" id="to" name="to">
"""
class EditTagForm(forms.Form):
    tagsForm = forms.CharField(widget=forms.Textarea)
