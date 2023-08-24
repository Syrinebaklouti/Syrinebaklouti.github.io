import openpyxl
import csv
from django.shortcuts import render
from django.http import HttpResponse
from openpyxl.utils import get_column_letter
from .forms import FileUploadForm
from django.shortcuts import redirect
import json
from io import BytesIO
import io
import tempfile
import os
from openpyxl.drawing.image import Image
import pandas as pd
import base64
import PyPDF2
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .forms import FileUploadForm, PDFUploadForm
from django.core.files.storage import FileSystemStorage
import re
import spacy
from django.template import loader




def generate_results(file1_contents, file2_contents):
    lines_to_check = file1_contents.splitlines()
    results = []

    for line in lines_to_check:
        keyword = line.split('==>', 1)[-1].strip()
        if keyword in file2_contents:
            result = (line, 'OK')
        else:
            result = (line, 'KO')
        results.append(result)

    global_test_result = 'OK' if all(status == 'OK' for _, status in results) else 'KO'

    return results, global_test_result



def extract_values(file2_contents):
    lines_to_check = [
        'conf_DEC_BTF_bFlagTestLeds',
        'conf_DEC_BTF_bFlagTestIr',
        'conf_DEC_BTF_bFlagTestSDCard',
        'conf_DEC_BTF_bFlagTestSmartCard',
        'conf_DEC_BTF_bFlagTestUsb',
        'conf_DEC_BTF_bFlagTestVentilateur',
        'conf_DEC_BTF_bFlagTestTemperatureChipset',
        'conf_DEC_BTF_bFlagTestLedsSequentiel',
        'conf_DEC_BTF_bFlagTestBoutonMute',
        'conf_DEC_BTF_bFlagTestBoutonMuteOFF',
        'conf_DEC_BTF_bFlagTestFlashNand',
        'conf_DEC_BTF_bFlagTestFlashNor',
        'conf_DEC_BTF_bFlagTestHdd',
    ]

    values = {}
    file2_lines = file2_contents.splitlines()

    for line in lines_to_check:
        for file2_line in file2_lines:
            if line.strip() in file2_line:
                keyword, value = file2_line.split(':', 1)
                keyword = keyword.strip()
                value = value.strip()
                values[keyword] = value

    return values

def generate_excel_file(results):
    df = pd.DataFrame(results, columns=['Test', 'Result'])

    excel_data = BytesIO()

    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)

    return excel_data.getvalue()



def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file1 = request.FILES.get('file1')
            file2 = request.FILES.get('file2')

            if file1 and file2:
                file1_contents = file1.read().decode('latin-1')
                file2_contents = file2.read().decode('latin-1')

                results, global_test_result = generate_results(file1_contents, file2_contents)
                values = extract_values(file2_contents)  
                workbook = generate_excel_file(results)

                request.session['results'] = results
                request.session['workbook'] = base64.b64encode(workbook).decode('utf-8')
                request.session['global_test_result'] = global_test_result
                request.session['values'] = values

                print("Files uploaded successfully!")
                return redirect('show_results')
        else:
            print("Form is not valid:", form.errors)
    else:
        form = FileUploadForm()

    return render(request, 'file_app/upload.html', {'form': form})




def check_global_test(results):
    if not results:
        return 'KO'
    for _, status in results:
        if status == 'KO':
            return 'KO'
    return 'OK'


def show_results(request):
    print("show_results")
    results = request.session.get('results', [])
    global_test_result = check_global_test(results)
    values = request.session.get('values', {})
    return render(request, 'file_app/success.html', {'results': results, 'global_test_result': global_test_result, 'values': values})


def download_results(request):
    workbook = request.session.get('workbook')
    if workbook:
        workbook_bytes = base64.b64decode(workbook.encode('utf-8'))
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=results.xlsx'
        response.write(workbook_bytes)
        return response
    return HttpResponse('No results found.')



def upload_pdf(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES['pdf_file']
            subtitles = extract_subtitles(pdf_file)
            return render(request, 'file_app/extract.html', {'subtitles': subtitles})
    else:
        form = PDFUploadForm()

    return render(request, 'file_app/upload_pdf.html', {'form': form})

def extract(request):
    subtitles = request.session.get('subtitles', None)
    if subtitles is not None:
        return render(request, 'file_app/extract.html', {'subtitles': subtitles})
    else:
        return HttpResponse("No subtitles to display.")

def download_subtitles(request):
    btf_keywords_mapping = {
        'SWITCH': 'BUTTONS TEST',
        'CHIPSET  SECURITY': 'CHIPSET TEMPERATURE TEST',
        'USB2': 'USB TEST',
        'LEDS': 'LEDS',
        'INFRARED': 'INFRARED',
        'NAND FLASH TEST': 'NAND FLASH TEST',  
        'VERIFYING AUTHORIZATION': 'VERIFYING AUTHORIZATION',  
        'TEST BOUTON MUTE': 'TEST BOUTON MUTE',  
        'TEST BOUTON MUTE OFF': 'TEST BOUTON MUTE OFF',  
    }

    bav_keywords_mapping = {
        'HDMI': 'test HDMI',
        'ETHERNET': 'Test ethernet',
        'USB2': 'Test Debit USB',
        'FT_HDMI_CEC': 'FT_HDMI_CEC',
        'BriqLogicielles':'BriqLogicielles',
        'InitDec':'InitDec',
        'TEST_ACCESSOIRES':'TEST_ACCESSOIRES',
    }

    subtitles = request.session.get('subtitles', None)
    if subtitles is not None:
        btf_subtitles = []
        bav_subtitles = []

        for subtitle in subtitles:
            tags = re.findall(r'\[([^]]+)\]', subtitle)
            if tags:
                tags_string = tags[len(tags) // 2]
                keyword = tags_string.strip().upper()
                if keyword in btf_keywords_mapping:
                    tag = btf_keywords_mapping[keyword]
                    if tag != '':
                        btf_subtitles.append(f"{tags_string} ==> {tag}")
                    else:
                        btf_subtitles.append(f"{tags_string} ==>")

                if keyword in bav_keywords_mapping:
                    tag = bav_keywords_mapping[keyword]
                    if tag != '':
                        bav_subtitles.append(f"{tags_string} ==> {tag}")
                    else:
                        bav_subtitles.append(f"{tags_string} ==>")

          
            if "[LEDS]" in subtitle:
                btf_subtitles.append("LEDS ==>")
                
        ft_hdmi_cec_tag = bav_keywords_mapping.get('FT_HDMI_CEC', None)
        if ft_hdmi_cec_tag:
            bav_subtitles.append(f"FT_HDMI_CEC ==> {ft_hdmi_cec_tag}")
            
        if 'download_subtitles_btf' in request.path:
            
            btf_additional_items = {
                'NAND FLASH TEST': 'NAND FLASH TEST',
                'VERIFYING AUTHORIZATION': 'VERIFYING AUTHORIZATION',
                'TEST BOUTON MUTE': 'TEST BOUTON MUTE',
                'TEST BOUTON MUTE OFF': 'TEST BOUTON MUTE OFF',
            }

            for item in btf_additional_items:
                tag = btf_additional_items[item]
                if tag != '':
                    btf_subtitles.append(f"{item} ==> {tag}")
                else:
                    btf_subtitles.append(f"{item} ==>")

            response = HttpResponse(content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="BTF_results.txt"'
            response.write("\n".join(btf_subtitles))
            return response

        if 'download_subtitles_bav' in request.path:
             bav_additional_items = {
            
                'BriqLogicielles':'BriqLogicielles',
                'InitDec':'InitDec',
                'TEST_ACCESSOIRES':'TEST_ACCESSOIRES',
            }

        for item in bav_additional_items:
                tag = bav_additional_items[item]
                if tag != '':
                    bav_subtitles.append(f"{item} ==> {tag}")
                else:
                    bav_subtitles.append(f"{item} ==>")
            
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="BAV_results.txt"'
        response.write("\n".join(bav_subtitles))
        return response

        return HttpResponse("No subtitles to download.")
    else:
        return HttpResponse("No subtitles to download.")


def extract_subtitles(pdf_file):
    subtitles = []
    with pdf_file.open(mode='rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        part_pattern = re.compile(r'Part\s+(\d+)\.\s+(.+)')  
        subtitle_pattern = re.compile(r'(\d+\.\d+)\s+(.+)')  
        dots_pattern = re.compile(r'(\s*\.\s*)+')  

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            lines = text.split('\n')
            is_functional_tests = False

            for line in lines:
                part_match = part_pattern.search(line)
                if part_match:
                    part_number = part_match.group(1)
                    subtitle_text = part_match.group(2)
                    if part_number.startswith('7'):
                        is_functional_tests = True
                        continue
                    else:
                        is_functional_tests = False

                if is_functional_tests:
                    subtitle_match = subtitle_pattern.search(line)
                    if subtitle_match:
                        subtitle_text = subtitle_match.group(2).strip()
                        subtitle_text = dots_pattern.sub('', subtitle_text)
                        
                        subtitle_text = re.sub(r'\d+$', '', subtitle_text).strip()

                        
                        if "LEDS" in subtitle_text:
                            subtitles.append(f"{subtitle_text} ==> LEDS")
                        else:
                            tags = re.findall(r'\[([^]]+)\]', subtitle_text)
                            if tags:
                                tags_string = tags[len(tags) // 2]
                                full_subtitle = f"{subtitle_text} ==> {tags_string}"
                                subtitles.append(full_subtitle)
                            else:
                                subtitles.append(subtitle_text)

    return subtitles