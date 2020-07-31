# Class 8 Utilities
# Functions that do not require database access
from flask import request
from webapp.utils import *
import datetime
today = datetime.datetime.today()



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

    if ckdigit == theckdigit:
        message = f'Container {num} is valid with cksum = {ckdigit}'
        return 0, message
    else:
        message = f'Container {num} is NOT valid: cksum = {ckdigit} does not match last digit {theckdigit}'
        return 2, message



def form_check(text,type):
    status = 0
    message = 'Type is not defined'
    print(text,type)

    if type == 'text':
        if not hasinput(text):
            text = ''
            status = 1
            message = 'Warning: This text data has no value'
        else:
            status = 0
            message = 'Ok'

    elif type == 'multitext':

        if not hasinput(text):
            text = ''
            status = 1
            message = 'Warning: This text data has no value'
        else:
            status = 0
            message = 'Ok'

    elif type == 'date':
        try:
            dt = datetime.datetime.strptime(text,'%Y-%m-%d')
            status = 0
            message = 'ok'
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

    elif type == 'concheck':
        if text is not None:
            lenck = len(text)
            if lenck == 11:
                status, message = container_check(text)
            else:
                if lenck > 0:
                    status = 2
                    message = f'Container must have length of 11 characters not {lenck}'
                else:
                    status = 1
                    message = f'No container information entered yet'

    elif type == 'container_types':
        print('select',text)
        if text == 'Choose Later':
            status = 1
            message = 'Warning: Make selection if possible'

    elif type == 'customerdata':
        print('select',text)
        if text == 'Choose Later':
            status = 2
            message = 'Error: must choose a customer'

    elif type == 'dropblock1':
        from webapp.class8_tasks import get_drop
        if not hasinput(text):
            loadname = request.values.get('dropblock1')
            if loadname is not None:
                text = get_drop(loadname)
        print('got dropblock1',text)

    elif type == 'dropblock2':
        from webapp.class8_tasks import get_drop
        if not hasinput(text):
            loadname = request.values.get('dropblock2')
            if loadname is not None:
                text = get_drop(loadname)
        print('got dropblock2',text)

    return text,status,message

def colorcode(incol):
    if isinstance(incol, int):
        if incol == 4: return 'green text-white font-weight-bold'
        elif incol == 3: return'amber font-weight-bold'
        elif incol == 2: return'purple text-white font-weight-bold'
        elif incol == 1: return 'blue text-white font-weight-bold'
        elif incol == -1: return 'yellow font-weight-bold'
        else: return 'white font-weight-bold'
    else:
        if incol == 'IO': return 'blue-text font-weight-bold'
        elif incol == 'BBBBBB': return'amber font-weight-bold'
        else: return 'white font-weight-bold'

def checked_tables(tables):
    cks = []
    for table in tables:
        cks.append(request.values.get(f'{table}box'))
    print(cks)
    return cks
