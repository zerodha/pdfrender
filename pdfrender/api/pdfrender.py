#!/bin/env python
# -*- coding: utf-8 -*-
"""
This RPC is used to fill a pdf with the response data.

Data is filled using pdf_text_overlay lib
"""

import json
import os
import uuid

import frappe

from frappe.utils import get_files_path

from pdf_text_overlay import pdf_writer


@frappe.whitelist()
def get_filled_pdf():
    """
    Receive template_id, data and returns a pdf file.

    Post the data to be filled on the pdf form
    The value of the key(name) in configuration data must be
    present as the key in the post data

    Call fill_pdf_form() method to fill the pdf form template

    """
    try:
        file_name = fill_pdf_form(
            json.loads(frappe.local.form_dict.data)
        )
    except KeyError as e:
        frappe.local.response['http_status_code'] = 400
        return {"error": "Key not found ", "key": e.message}
    except ValueError as e:
        frappe.local.response['http_status_code'] = 400
        return {"error": e.message}
    except IOError as e:
        frappe.local.response['http_status_code'] = 400
        return {"error": e.message}

    # Read contents of file
    frappe.local.response.filename = "response.pdf"
    with open(file_name, "rb") as fileobj:
        filedata = fileobj.read()

    # Set response type and response file content
    frappe.local.response.filecontent = filedata
    frappe.local.response.type = "download"

    # Delete file after reading the file contents
    delete_file(file_name)

    return "Success"


def fill_pdf_form(post_data):
    """
    Receive template_id and post_data and returns a file_name.

    New pdf file is created to store the response of pdf_text_overlay library
    Call pdf_text_overlay library to fill the pdf form

    :param post_data: post_data is the data which
                        is used to fill the pdf
     """
    # Get template, configuration and font from doctype using template id
    data = frappe.get_all(
        'Templates',
        filters={"templateId": post_data['template_id']},
        fields=['template', 'configuration', 'font']
    )

    try:
        data, = data
    except ValueError:
        raise ValueError(
            'Could not find data for template ID: {}'.format(
                post_data['template_id'])
        )

    font_path = frappe.get_doc('Fonts', data['font'])
    template_path = data["template"]
    configuration = data["configuration"]

    # Read font file and pdf template
    try:
        font = file(get_file_path(font_path.font_name), "rb")
        pdf_template = file(get_file_path(template_path), "rb")
    except IOError as io:
        raise IOError('File not found: {}'.format(io.filename))

    # Create a unique file name using uuid
    file_name = str(uuid.uuid4()) + '.pdf'

    # Fill the Pdf using pdf_text_overlay library
    pdf_file_object = pdf_writer(
        pdf_template, json.loads(configuration),
        post_data, font
    )

    # Save the pdf_file_object to a file for further operations
    output_stream = file(file_name, "wb")
    pdf_file_object.write(output_stream)
    output_stream.close()

    return file_name


def get_file_path(file_path):
    """File path."""
    if "/" not in file_path:
        file_path = "/files/" + file_path

    if file_path.startswith("/private/files/"):
        file_path = get_files_path(
            *file_path.split("/private/files/", 1)[1].split("/"), is_private=1)

    elif file_path.startswith("/files/"):
        file_path = get_files_path(
            *file_path.split("/files/", 1)[1].split("/"))

    else:
        frappe.throw(
            "There is some problem with the file url: {0}").format(file_path)
    return file_path


def delete_file(file_name):
    """
    Delete a file if exists.

    :param file_name: the file_name is used to delete the file
    """
    if os.path.exists(file_name):
        os.remove(file_name)
