import os

from django import forms
from django.conf import settings


class SearchForm(forms.Form):
    query = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Search for an image...'}), max_length=100, required=False)


class SearchForImageForm(forms.Form):
    image = forms.ImageField(label="", required=False)


class EditFoldersForm(forms.Form):
    path = forms.FilePathField(label="", path=os.getenv("HOME"), required=False)

