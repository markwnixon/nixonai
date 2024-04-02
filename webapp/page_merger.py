from PyPDF2 import PdfReader, PdfWriter
#from PyPDF2 import PageObject
from webapp.CCC_system_setup import myoslist, addpath, addpath2, addtxt, scac
import os
import subprocess
import shutil


def pagemerger(filelist, cache):

    lfs = len(filelist)-1
    print('lfs has value:', lfs)

    for j in range(lfs):

        if j == 0:
            firstfile = filelist[0]
        else:
            firstfile = addpath(f'static/{scac}/data/vreport/temp'+str(j-1)+'.pdf')

        reader = PdfReader(open(firstfile, 'rb'))
        first_page = reader.pages[0]

        sup_reader = PdfReader(open(filelist[j+1], 'rb'))
        sup_page = sup_reader.pages[0]  # This is the first page, can pick any page of document

    #translated_page = PageObject.createBlankPage(None, sup_page.mediaBox.getWidth(), sup_page.mediaBox.getHeight())
    # translated_page.mergeScaledTranslatedPage(sup_page, 1, 0, 0)  # -400 is approximate mid-page
    # translated_page.merge_page(invoice_page)
        sup_page.merge_page(first_page)
        writer = PdfWriter()
    # writer.add_page(translated_page)
        writer.add_page(sup_page)

        if j == lfs-1:
            outfile = addpath(f'static/{scac}/data/vreport/report'+str(cache)+'.pdf')
        else:
            outfile = addpath(f'static/{scac}/data/vreport/temp'+str(j)+'.pdf')

        print('lfs and j are:', j, lfs)
        print('firstfile=', firstfile)
        print('supfile=', filelist[j+1])
        print('outfile=', outfile)

        with open(outfile, 'wb') as f:
            writer.write(f)

        f.close()

    docref = f'static/{scac}/data/vreport/report'+str(cache)+'.pdf'
    killfile = addpath(f'static/{scac}/data/vreport/report'+str(cache-1)+'.pdf')
    try:
        os.remove(killfile)
    except:
        print('Could not remove previous file')
    cache = cache+1
    if cache == 999:
        cache = 0
    print('The value of cache is:', cache)
    return cache, docref


def pagemergerx(filelist, page, cache):

    lfs = len(filelist)-1
    print('lfs has value:', lfs)

    for j in range(lfs):

        if j == 0:
            firstfile = filelist[0]
        else:
            firstfile = addpath(f'static/{scac}/data/vreport/temp'+str(j-1)+'.pdf')

        reader = PdfReader(open(firstfile, 'rb'))
        first_page = reader.pages[page]

        sup_reader = PdfReader(open(filelist[j+1], 'rb'))
        sup_page = sup_reader.pages[0] # This is the selected page, can pick any page of document

    #translated_page = PageObject.createBlankPage(None, sup_page.mediaBox.getWidth(), sup_page.mediaBox.getHeight())
    # translated_page.mergeScaledTranslatedPage(sup_page, 1, 0, 0)  # -400 is approximate mid-page
    # translated_page.merge_page(invoice_page)
        sup_page.merge_page(first_page)
        writer = PdfWriter()
    # writer.add_page(translated_page)
        writer.add_page(sup_page)

        if j == lfs-1:
            outfile = addpath(f'static/{scac}/data/vreport/report'+str(cache)+'.pdf')
        else:
            outfile = addpath(f'static/{scac}/data/vreport/temp'+str(j)+'.pdf')

        print('lfs and j are:', j, lfs)
        print('firstfile=', firstfile)
        print('supfile=', filelist[j+1])
        print('outfile=', outfile)

        with open(outfile, 'wb') as f:
            writer.write(f)

        f.close()

    docref = f'static/{scac}/data/vreport/report'+str(cache)+'.pdf'
    killfile = addpath(f'static/{scac}/data/vreport/report'+str(cache-1)+'.pdf')
    try:
        os.remove(killfile)
    except:
        print('Could not remove previous file')
    cache = cache+1
    if cache == 999:
        cache = 0
    print('The value of cache is:', cache)
    return cache, docref


def pagemergermp(filelist, cache, pages, multioutput):

    lfs = len(filelist)-1
    print('lfs has value:', lfs)

    for j in range(lfs):

        if j == 0:
            firstfile = filelist[0]
        else:
            firstfile = addpath(f'static/{scac}/data/vreport/temp'+str(j-1)+'.pdf')

        reader = PdfReader(open(firstfile, 'rb'))
        first_page = reader.pages[0]

        sup_reader = PdfReader(open(filelist[j+1], 'rb'))
        sup_page = sup_reader.pages[0] # This is the first page, can pick any page of document

    #translated_page = PageObject.createBlankPage(None, sup_page.mediaBox.getWidth(), sup_page.mediaBox.getHeight())
    # translated_page.mergeScaledTranslatedPage(sup_page, 1, 0, 0)  # -400 is approximate mid-page
    # translated_page.merge_page(invoice_page)
        sup_page.merge_page(first_page)
        writer = PdfWriter()
    # writer.add_page(translated_page)
        writer.add_page(sup_page)

        if j == lfs-1:
            outfile = addpath(f'static/{scac}/data/vreport/report'+str(cache)+'.pdf')
        else:
            outfile = addpath(f'static/{scac}/data/vreport/temp'+str(j)+'.pdf')

        print('lfs and j are:', j, lfs)
        print('firstfile=', firstfile)
        print('supfile=', filelist[j+1])
        print('outfile=', outfile)

        with open(outfile, 'wb') as f:
            writer.write(f)

        f.close()

    # This gives us the merges backdrop pdf file on which we will place the contents.
    # Now place the mulitpage content on this file for each page and assemble
    newpages = []
    for j, page in enumerate(pages):
        reader = PdfReader(open(outfile, 'rb'))
        first_page = reader.pages[0]

        sup_reader = PdfReader(open(multioutput, 'rb'))
        sup_page = sup_reader.pages[j]

        sup_page.merge_page(first_page)
        writer = PdfWriter()
        writer.add_page(sup_page)

        newoutfile = addpath2('multipage'+str(j)+'.pdf')
        with open(newoutfile, 'wb') as f:
            writer.write(f)

        f.close()
        newpages.append(newoutfile)

    pdfcommand = ['pdfunite']
    for page in newpages:
        pdfcommand.append(page)
    newmultioutput = addpath(f'static/{scac}/data/vreport/newmultioutput'+str(cache)+'.pdf')
    pdfcommand.append(newmultioutput)
    tes = subprocess.check_output(pdfcommand)

    docref = f'static/{scac}/data/vreport/report'+str(cache)+'.pdf'
    shutil.move(newmultioutput, addpath(docref))

    killfile = addpath(f'static/{scac}/data/vreport/report'+str(cache-1)+'.pdf')
    try:
        os.remove(killfile)
    except:
        print('Could not remove previous file')
    cache = cache+1
    if cache == 999:
        cache = 0
    print('The value of cache is:', cache)
    return cache, docref
