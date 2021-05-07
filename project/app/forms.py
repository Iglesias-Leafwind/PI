import os

from django import forms
from string import Template
from django.utils.safestring import mark_safe


class PictureWidget(forms.widgets.Widget):
    def render(self, name, value, attrs=None, **kwargs):
        html = Template("""<img src="$link"/>""")
        return mark_safe(html.substitute(link=value))


class SearchForm(forms.Form):
    query = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Search for an image...'}), max_length=100, required=False)


class SearchForImageForm(forms.Form):
    image = forms.ImageField(label="", required=False)


class EditFoldersForm(forms.Form):
    path = forms.CharField(label="Add new folder:", widget=forms.Select(choices=tuple([(choice, choice) for choice in ['ola', 'adeus']]), attrs={'style': 'width:180px'}))


class PersonsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #people = Person.objects.all()
        for i in range(8): # for i in range(len(people))
            field_name = 'person_image_%s' % (i,)
            field_image = 'person_name_%s' % (i,)
            self.fields[field_image] = forms.ImageField(required=False, widget=PictureWidget)
            self.fields[field_name] = forms.CharField(required=False)
            # self.initial[field_image] = people[i].icon
            # self.initial[field_name] = people[i].name

    def get_interest_fields(self):
        for field_name in self.fields:
            if field_name.startswith('person_'):
                yield self[field_name]
