from django import forms
from string import Template

from django.forms import CheckboxInput, HiddenInput
from django.utils.safestring import mark_safe

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


class PersonsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        people = Person.nodes.all()

        all_rels = [ (person.image.relationship(img), person, img) for person in people for img in person.image.all() ]

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
            self.initial[field_name] = rel[1].name + ' -- ' + str(rel[0].confiance)
            self.initial[field_person_before] = rel[1].name
            self.initial[field_image_id] = rel[2].hash
            self.initial[field_verified] = rel[0].approved
            # self.initial[field_verified] = True if rel[0].confiance > 0.5 else False



    def get_interest_fields(self):
        for field_name in self.fields:
            if field_name.startswith('person_'):
                yield self[field_name]

class EditTagForm(forms.Form):
    tagsForm = forms.CharField(widget=forms.Textarea)
