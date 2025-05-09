# Class 8 Utilities
# Functions that do not require database access
from flask import request
from webapp.utils import *
import datetime
import math
from webapp.models import Orders
today = datetime.datetime.today()

def sameall(lst):
    digfor = True
    for item in lst:
        if item != lst[0]: digfor = False
    return digfor

def container_check(num):
    check1 = 0
    alphadigit = {'A': '10', 'B': '12', 'C': '13', 'D': '14', 'E': '15', 'F': '16', 'G': '17', 'H': '18', 'I': '19',
                  'J': '20', 'K': '21', 'L': '23', 'M': '24', 'N': '25', 'O': '26', 'P': '27', 'Q': '28', 'R': '29',
                  'S': '30', 'T': '31', 'U': '32', 'V': '34', 'W': '35', 'X': '36', 'Y': '37', 'Z': '38'
                  }
    for jx, digit in enumerate(num):
        if jx == 10:
            theckdigit = int(digit)
        else:
            try:
                value = int(digit)
            except:
                value = int(alphadigit[digit])

            check1 = check1 + value * 2 ** jx

    ckdigit = check1 - int(check1 / 11) * 11
    if ckdigit == 10: ckdigit = 0

    if ckdigit == theckdigit:
        message = f'Container {num} is valid with cksum = {ckdigit}'
        return 0, message
    else:
        message = f'Container {num} is NOT valid: cksum = {ckdigit} does not match last digit {theckdigit}'
        return 2, message


def form_check(input,text,type,task,req, task_iter, haultype, sid, itable):
    #print(' ')
    ###print(f'Checking input for input:{input} text:{text} haultype:{haultype}, type:{type} task:{task} required:{req} task_iter: {task_iter}')
    status = 0
    message = ''
    if type == 'disabled':
        #print('returning disabled')
        return text, status, message


    if type == 'text':
        if not hasinput(text):
            text = ''
            status = 2
            message = 'Error: This text data has no value'
        else:
            status = 0
            message = 'Ok'
            text = text.strip()

    elif type == 'multitext':

        if not hasinput(text):
            text = ''
            status = 2
            message = 'Error: This text data has no value'
        else:
            status = 0
            message = 'Ok'

    elif type == 'date':
        if isinstance(text, datetime.date):
            #print('date is in datetime format')
            status = 0
            message = 'ok'
        else:
            try:
                dt = datetime.datetime.strptime(text,'%Y-%m-%d')
                status = 0
                message = 'ok'
                #print(f'date {text} is text that can be converted')
            except:
                text = today.strftime('%Y-%m-%d')
                status = 1
                message = 'Warning: No date time entered so date set to today'

    elif type == 'float':
        try:
            dt = float(text)
            text = d2s(dt)
            status = 0
            message = 'ok'
        except:
            status = 2
            message = 'Error: must set a numerical value for this charge'

    elif type == 'amtpaid':
        if task == 'PayBill':
            try:
                dt = float(text)
                text = d2s(dt)
                status = 0
                message = 'ok'
            except:
                status = 2
                message = 'Error: must set a numerical value for this payment'
        else:
            try:
                dt = float(text)
                text = d2s(dt)
                status = 0
                message = 'ok'
            except:
                status = 1
                message = 'Warning: this must be set when paying, but not for edit'

    elif type == 'integer':
        try:
            dt = int(text)
            text = str(dt)
            status = 0
            message = 'ok'
        except:
            status = 2
            message = 'Error: must set a numerical value for this value'

    elif type == 'concheck':
        #Complex checker.  We want to assess ligitimate containers for proper number
        #but allow for exceptions or use of dry vans and other container types...etc
        if not hasinput(text) and not hasinput(haultype) and req:
            status = 2
            message = f'Valid container number input required'
            return text, status, message
        else:
            #if not hasinput(text) and req: text = 'Missing'
            if text is not None: text = text.strip()
            else: text = ''
            ###print(f'****************************Entering concheck with text {text}')
            if hasinput(text): char1 = text[0]
            else: char1 = ''
            if char1 == '*':
                status = 0
                message = 'Forced bypass number'
            else:
                if haultype is None:
                    if not hasinput(text) or task_iter == 0:
                        status = 0
                        message = 'Not a required input yet'
                    else:
                        lenck = len(text)
                        if lenck == 11:
                            status, message = container_check(text)

                        else:
                            if lenck > 3:
                                status = 2
                                message = f'Container must have length of 11 characters not {lenck}'
                            else:
                                status = 2
                                message = f'Valid container number input required'

                else:
                    if 'Dray' in haultype or 'Export' in haultype or 'Import' in haultype:
                        if hasinput(text):
                            lenck = len(text)
                            if lenck == 11:
                                status, message = container_check(text)
                                #print(f'Container status check: {status} {message}')
                            else:
                                if lenck > 0:
                                    status = 2
                                    message = f'Container must have length of 11 characters not {lenck}'
                                else:
                                    status = 2
                                    message = f'Valid container number input required'
                        else:
                            if 'Import' in haultype:
                                status = 2
                                message = 'Must enter a valid container number'
                            else:
                                status = 1
                                message = 'Container number required after pull'
                    else:
                        status = 0
                        message = 'Not a required input for haul type'

    elif type == 'release':
        #Complex checker.  We want to assess ligitimate bookings for proper number
        #but allow for exceptions or use of dry vans and other container types...etc
        if haultype is None:
            status = 1
            message = 'Not a required input yet'
        else:
            if itable == 'Orders':
                if 'Dray' in haultype or 'Export' in haultype or 'Import' in haultype:
                    if text is not None:
                        text = text.strip()
                        lenck = len(text)

                        if lenck < 4:
                            status = 2
                            message = f'Must have at least 4 characters not {lenck}'
                        else:
                            status = 0
                            if 'Export' in haultype: message = 'Booking number entered'
                            if 'Import' in haultype: message = 'BOL number entered'
                    else:
                        status = 2
                        if 'Export' in haultype: message = 'Must enter a booking number'
                        if 'Import' in haultype: message = 'Must enter a BOL number'

                else:
                    status = 0
                    message = 'Not a required input for this haul type'
            if itable == 'Interchange':
                if haultype == 'Empty Out' or haultype == 'Load In':
                    req = True
                    if not hasinput(text):
                        status = 2
                        message = 'Booking release required for Empty Out'


    elif type == 'container_types':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a container type'

    elif type == 'load_types':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a container type'


    elif type == 'pickupdata':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a pick up location'

    elif type == 'haul_types':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a haul type'

    elif type == 'customerdata':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a customer'

    elif type == 'terminaldata':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a terminal'

    elif type == 'shipdata':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must select a ship'

    elif type == 'vendordata':
        if text == 'Choose Later':
            status = 2
            message = 'Error: must choose a vendor'
        elif not hasinput(text):
            status = 2
            message = 'Must choose the vendor'

    elif type == 'driverdata':
        if text == 'Choose Later' or not hasinput(text):
            status = 2
            message = 'Must choose a driver'
        else:
            status = 0
            message = 'Driver selected'

    elif type == 'codata':
        #print('select',text)
        if text == 'Choose Later':
            status = 2
            message = 'Error: must associate bill with Co/Div'
        elif not hasinput(text):
            status = 2
            message = 'Must choose the responsible Co/Div for the Bill'

    elif type == 'expdata':
        #print('select',text)
        if text == 'Choose Later':
            status = 2
            message = 'Error: must associate bill with pay account'
        elif not hasinput(text):
            status = 2
            message = 'Must choose the responsible billing account for the Bill'

    elif type == 'acctdata':
        #print('select',text)
        if text == 'Choose Later':
            if task == 'PayBill':
                status = 2
                message = 'Error: must a payment account'
            else:
                status = 1
                message = 'Warning: this must be set when paying bill'

    elif type == 'paymethods':
        #print('select',text,task)
        if text == 'Choose Later':
            if task == 'PayBill':
                status = 2
                message = 'Error: must include a payment method'
            else:
                status = 1
                message = 'Warning: this must be set when paying bill'

    elif type == 'dropblock1' or type == 'dropblock2' or type == 'dropblock3':
        from webapp.class8_tasks import get_drop, Review_Drop, get_terminal
        noterminals = ['OTR', 'Box Truck', 'Transload Only', 'Transload-Deliver']
        secterminal = ['Dray Import 2T', 'Dray Export 2T']
        secstop = ['Import Extra Stop', 'Export Extra Stop']
        if haultype in secterminal: secterm = 1
        else: secterm = 0
        if haultype in noterminals: noterm = 1
        else: noterm = 0
        if haultype in secstop: secst = 1
        else: secst = 0

        #print(f'In form check for dropblocks, dropblock:{type}, haultype:{haultype} secterm: {secterm} noterm: {noterm} secstop: {secst}')
        if type == 'dropblock1' or type == 'dropblock3':
            if not noterm:
                #print(f'*********************starting this test for type {type} with text: {text}')
                if hasinput(text):
                    testtext = text.strip()
                    #print(f'The length of testtest is {len(testtext)}')
                    if len(testtext) < 6:
                        text = get_drop(testtext)
                        text = Review_Drop(text)
                if not hasinput(text):
                    loadname = request.values.get(type)
                    #print(f'loadname:{loadname},type:{type},text:{text}')
                    if loadname is not None:
                        if type == 'dropblock3' and secstop:
                            text = get_drop(loadname)
                            #print(f'text from get_drop:{text}')
                        else:
                            text = get_terminal(loadname)
                            #print(f'text from get_terminal:{text}')
                if not hasinput(text) and task_iter > 0:
                    status = 2
                    message = 'Must include this location information'

            else:
                # print(f'*********************starting this test for type {type} with text: {text}')
                if hasinput(text):
                    testtext = text.strip()
                    #print(f'The length of testtest is {len(testtext)}')
                    if len(testtext) < 6:
                        text = get_drop(testtext)
                if not hasinput(text):
                    loadname = request.values.get(type)
                    #print(f'loadname:{loadname},type:{type},text:{text}')
                    if loadname is not None:
                        text = get_drop(loadname)
                        #print(f'text:{text}')
                if not hasinput(text) and task_iter > 0:
                    status = 2
                    message = 'Must include this location information'


        else:

            #print(f'*********************starting this test for type {type} with text: {text}')
            if hasinput(text):
                testtext = text.strip()
                #print(f'The length of testtest is {len(testtext)}')
                if len(testtext) < 6:
                    text = get_drop(testtext)
            if not hasinput(text):
                loadname = request.values.get(type)
                #print(f'loadname:{loadname},type:{type},text:{text}')
                if loadname is not None:
                    text = get_drop(loadname)
                    #print(f'text:{text}')
            if not hasinput(text) and task_iter > 0:
                status = 2
                message = 'Must include this location information'

        # Check to see if need to add new drop to drop database
        if hasinput(text):
            text = Review_Drop(text)

    elif type == 'emaildata1' or type == 'emaildata2' or type == 'emaildata3':
        #from webapp.class8_tasks import get_emailset
        #print(f'*********************starting this test for type {type} with text: {text}')
        if hasinput(text):
            text = text.strip()
            if text == '':
                text = request.values.get(type)
        if not hasinput(text):
            text = request.values.get(type)
            if text is not None:
                text = text.strip()
            else:
                text = ''
        if not hasinput(text) and task_iter > 0:
            status = 1
            message = 'Should include this email information'

    elif type == 'quotehistory':
        sh = request.values.get('Shipper')
        ld = request.values.get('Dropblock2')

        if not hasinput(text) or 'History' in text:
            if hasinput(sh) and not hasinput(ld):
                #initiate the values from previous history
                text = f'No history {sh}'
            if hasinput(sh) and hasinput(ld):
                coz = ld.splitlines()
                co = coz[0].strip()
                gdat = Orders.query.filter((Orders.Shipper == sh) & (Orders.Company2 == co) & (Orders.Amount != '')).order_by(Orders.id.desc()).first()
                if gdat is not None:
                    #print(f'Search for history with sh {sh} and co {co} found the *{gdat.Amount}*')
                    bc = gdat.Amount
                    qh = gdat.Quote
                    if input == 'Amount':
                        text = bc
                    if input == 'Quote':
                        text = qh
                else:
                    text=f'History for {sh} not found'
        else:
            #The input has a value provided so try to convert to a dollar value
            text = text.strip()
            try:
                dt = float(text)
                text = d2s(dt)
                status = 0
                message = 'ok'
            except:
                status = 1
                message = 'Warning: could not set a numerical value for this input'
    else:
        status = 2
        message = 'Input Required but not Found'
        if not hasinput(text): text = ''


    if not req:
        status = 0
        message = 'Not a Required Input'
        if not hasinput(text): text = ''

    ###print(f'At conclusion of input for input:{input} type: {type} text:{text} task:{task} required:{req};;;;status: {status} and message:{message}')

    return text, status, message

def colorcode(table, incol):
    #print(f'This table for color is {table}')
    if table == 'Orders':
        if incol == 5: return 'green text-white font-weight-bold'
        elif incol == 3: return'amber font-weight-bold'
        elif incol == 2: return'purple text-white font-weight-bold'
        elif incol == 1: return 'blue text-white font-weight-bold'
        elif incol == -1: return 'yellow font-weight-bold'
        elif incol == 6: return 'grey white-text font-weight-bold'
        elif incol == 7: return 'orange font-weight-bold'
        elif incol == 8: return 'light-green font-weight-bold'
        elif incol == 4: return 'black text-white font-weight-bold'
        else: return 'white font-weight-bold'
    elif table == 'Newjobs':
        if incol == 5: return 'green text-white font-weight-bold'
        elif incol == 3: return'amber font-weight-bold'
        elif incol == 2: return'purple text-white font-weight-bold'
        elif incol == 1: return 'blue text-white font-weight-bold'
        elif incol == -1: return 'yellow font-weight-bold'
        elif incol == 6: return 'grey white-text font-weight-bold'
        elif incol == 7: return 'orange font-weight-bold'
        elif incol == 8: return 'light-green font-weight-bold'
        elif incol == 4: return 'black text-white font-weight-bold'
        else: return 'white font-weight-bold'
    elif table == 'Interchange':
        if incol == 'IO': return 'blue-text font-weight-bold'
        elif incol == 'BBBBBB': return'amber font-weight-bold'
        else: return 'white font-weight-bold'
    elif table == 'SumInv':
        incol = int(incol)
        #print(f'Incol is {incol}')
        if incol == 1: return 'grey white-text font-weight-bold'
        elif incol == 2: return 'orange font-weight-bold'
        elif incol == 3: return 'black white-text font-weight-bold'
        elif incol == 4: return 'light-green text-white font-weight-bold'
        else: return 'white font-weight-bold'
    elif table == 'Bills':
        #print(f'Incol is {incol}')
        if incol == 'Paid': return 'green text-white font-weight-bold'
        elif incol == 'Part': return'amber font-weight-bold'
        else: return 'white font-weight-bold'
    else:
        return 'white font-weight-bold'

def checked_tables(tables):
    cks = []
    for table in tables:
        cks.append(request.values.get(f'{table}box'))
    #print('class8_utils.py 142 checked_tables() These are the checked tables:',cks)
    return cks

def checkfor_fileupload(err, task_iter, viewport):
    #print('utils.py 146 Setting form upload with task_iter:', task_iter)
    if task_iter == 1:
        viewport[0] = 'upload_doc_left'
    else:
        viewport[0] = request.values.get('viewport0')
        viewport[2] = request.values.get('viewport2')

    uploadnow = request.values.get('uploadnow')
    if uploadnow is not None:
        viewport[0] = 'show_doc_left'
        file = request.files['docupload']
        if file.filename == '':
            err.append('No source file selected for uploading')

        name, ext = os.path.splitext(file.filename)
        filename1 = f'Source_{name}{ext}'
        output1 = addpath(tpath('temp', filename1))
        file.save(output1)
        viewport[2] = f'/static/{scac}/data/temp/{filename1}'
        #print('the source doc is....', viewport[2])

    return err, viewport

#Utility for printing out a barcode from an address


#Utilities for turning numbers into words (like for check writing)

def once(num):
    one = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    word = ''
    word = one[int(num)]
    word = word.strip()
    return word

def ten(num):
    tenp = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tenp2 = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    word = ''
    if num[0] == '1':
        word = tenp[int(num[1])]
    else:
        text = once(num[1])
        word = tenp2[int(num[0])]
        word = word + "-" + text
    word = word.strip()
    return word

def hundred(num):
    one = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    word = ''
    text = ten(num[1:])
    word = one[int(num[0])]
    if num[0] != '0':
        word = word + "-Hundred "
    word = word + text
    word = word.strip()
    return word

def thousand(num):
    one = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    word = ''
    pref = ''
    text = ''
    length = len(num)
    if length == 6:
        text = hundred(num[3:])
        pref = hundred(num[:3])
    if length == 5:
        text = hundred(num[2:])
        pref = ten(num[:2])
    if length == 4:
        text = hundred(num[1:])
        word = one[int(num[0])]
    if num[0] != '0' or num[1] != '0' or num[2] != '0':
        word = word + "-Thousand "
    word = word + text
    if length == 6 or length == 5:
        word = pref + word
    word = word.strip()
    return word

def million(num):
    word = ''
    pref = ''
    text = ''
    length = len(num)
    if length == 9:
        text = thousand(num[3:])
        pref = hundred(num[:3])
    if length == 8:
        text = thousand(num[2:])
        pref = ten(num[:2])
    if length == 7:
        text = thousand(num[1:])
        word = one[int(num[0])]
    if num[0] != '0' or num[1] != '0' or num[2] != '0':
        word = word + " Million "
    word = word + text
    if length == 9 or length == 8:
        word = pref + word
    word = word.strip()
    return word

def get_check_words(num):
    val1 = float(num)
    val2 = math.floor(val1)
    #print(val2)
    val3 = val1-val2
    val3 = round(val3*100)
    #print(val3)
    a = str(val2)
    leng = len(a)
    if leng == 1:
        if a == '0':
            num = 'Zero'
        else:
            num = once(a)
    if leng == 2:
        num = ten(a)
    if leng == 3:
        num = hundred(a)
    if leng > 3 and leng < 7:
        num = thousand(a)
    if leng > 6 and leng < 10:
        num = million(a)

    lnum = len(num)
    ##print(num[lnum-1])
    if num[lnum-1] == '-':
        num = num[0:lnum-1]

    tval3 = "{0:0=2d}".format(val3)
    amount_text = num + ' and ' + tval3 + '/100 '
    return amount_text