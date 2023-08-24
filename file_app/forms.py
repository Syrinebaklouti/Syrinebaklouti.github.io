from django import forms

class FileUploadForm(forms.Form):
       file1 = forms.FileField(label='File 1')
       file2 = forms.FileField(label='File 2')
       #file3 = forms.FileField(label='File 3')
       
       
class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(label='Select PDF File')