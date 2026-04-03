from flask import render_template, flash, redirect, url_for, session, logging, request
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import ntpath
import shutil
import os
from CCC_system_setup import addpath
from CCC_system_setup import websites, passwords, companydata, scac, imap_url
from CCC_system_setup import usernames as em

import socket
import time
import imaplib
import ssl


def send_mimemail(emaildata,emailsender):

    ourserver = websites['mailserver']
    #emaildata is packed as emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2]

    emailfrom = em[emailsender]
    username = em[emailsender]
    password = passwords[emailsender]

    etitle = emaildata[0]
    ebody = emaildata[1]
    emailin1 = emaildata[2]
    emailin2 = emaildata[3]
    emailcc1 = emaildata[4]
    emailcc2 = emaildata[5]

    msg = MIMEMultipart()
    msg["From"] = emailfrom
    if emailcc2:
        msg["CC"] = f'{emailcc1}, {emailcc2}'
    elif emailcc1:
        msg["CC"] = f'{emailcc1}'
    if emailin2:
        msg["To"] = f'{emailin1}, {emailin2}'
    else:
        msg["To"] = f'{emailin1}'

    from_dom = emailfrom.split('@')[1]
    #print(f'from send_mimemail in send_mimemail.py: the domain is: {from_dom}')
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid(domain=from_dom)

    emailto=[emailin1]
    if emailin2 is not None:
        emailto.append(emailin2)
    if emailcc1 is not None:
        emailto.append(emailcc1)
    if emailcc2 is not None:
        emailto.append(emailcc2)

    msg["Subject"] = etitle
    msg.attach(MIMEText(ebody, 'html'))

    if 1 == 2:
        attachment = open(newfile, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % newfile)
        msg.attach(part)

    #print('username=',username,password,ourserver)
    [host, port] = ourserver.split(':')
    #print(host)
    #print(port)
    #server = smtplib.SMTP('smtppro.zoho.com')
    try:
        # Attempt to create the SMTP object and connect
        server = smtplib.SMTP(host, port)
        #server = smtplib.SMTP(smtp_server, smtp_port)
        print("Successfully connected to the SMTP server.")
        # Further actions with the server object (e.g., starttls, login, sendmail)
        server.starttls()
        print("Started TTLS")
        server.login(username, password)
        print("Server logged in")
        server.sendmail(emailfrom, emailto, msg.as_string())
        print("Sent the email")
        server.quit()

    except smtplib.SMTPConnectError as e:
        print(f"SMTP connection error: {e}")
        print("Possible causes: Incorrect server address or port, firewall issues, server not reachable.")
    except socket.gaierror as e:
        print(f"Address resolution error: {e}")
        print("Possible causes: Incorrect hostname, no internet connection, DNS issues.")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP server disconnected prematurely: {e}")
        print("Possible causes: Server issues, connection timeout.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")




    #server.starttls()
    #server.login(username,password)
    #server.sendmail(emailfrom, emailto, msg.as_string())
    #server.quit()

    return emailin1

def get_sent_folder(imap):
    status, folders = imap.list()
    if status != 'OK' or not folders:
        return 'Sent'

    for f in folders:
        line = f.decode() if isinstance(f, bytes) else str(f)
        print('the line is:' + line)

        if '\\Sent' in line:
            # mailbox name is the last field in the LIST response
            folder = line.rsplit(' ', 1)[-1].strip()
            folder = folder.strip('"')
            print(f"Detected Sent folder: {folder}")
            return folder

    return 'Sent'



def append_to_sent_folder(raw_msg_bytes, emailsender, sent_folder='Sent'):
    """
    Save the exact sent message to the IMAP Sent folder.
    """
    username = em[emailsender]
    password = passwords[emailsender]

    print(f'the imap url is {imap_url}')
    if scac.lower() == 'fela': sent_folder = 'INBOX.Sent'
    else: sent_folder = 'Sent'

    try:
        imap = imaplib.IMAP4_SSL(imap_url)
        imap.login(username, password)

        # If you want to verify the real folder name, uncomment:
        # status, folders = imap.list()
        # print('IMAP folders:', folders)
        #sent_folder = get_sent_folder(imap)

        imap.append(
            f'"{sent_folder}"',
            '\\Seen',
            imaplib.Time2Internaldate(time.time()),
            raw_msg_bytes
        )

        try:
            imap.close()
        except Exception:
            pass
        imap.logout()
        print(f"Saved sent message to IMAP folder: {sent_folder}")

    except Exception as e:
        print(f"Could not save message to Sent folder: {e}")


def send_replymail(emaildata, emailsender, sent_folder='Sent'):
    """
    emaildata dictionary format:

    {
        'subject': str,
        'body_html': str,
        'to_1': str,
        'to_2': str,
        'cc_1': str,
        'cc_2': str,
        'send_mode': 'direct' or 'reply',
        'save_sent': True or False,
        'original_message_id': str,
        'references': str,
    }
    """

    ourserver = websites['mailserver']

    emailfrom = em[emailsender]
    username = em[emailsender]
    password = passwords[emailsender]

    imap_host = imap_url.lower()
    is_zoho = 'zoho' in imap_host
    is_gmail = 'gmail' in imap_host

    etitle = emaildata.get('subject', '') or ''
    ebody = emaildata.get('body_html', '') or ''
    emailin1 = emaildata.get('to_1', '') or ''
    emailin2 = emaildata.get('to_2', '') or ''
    emailcc1 = emaildata.get('cc_1', '') or ''
    emailcc2 = emaildata.get('cc_2', '') or ''

    send_mode = emaildata.get('send_mode', 'direct') or 'direct'
    save_sent = bool(emaildata.get('save_sent', False))
    original_message_id = (emaildata.get('original_message_id', '') or '').strip()
    references = (emaildata.get('references', '') or '').strip()

    msg = MIMEMultipart()
    msg["From"] = emailfrom

    # Build CC header
    cc_list = []
    if emailcc1:
        cc_list.append(emailcc1)
    if emailcc2:
        cc_list.append(emailcc2)
    if cc_list:
        msg["CC"] = ', '.join(cc_list)

    # Build TO header
    to_list = []
    if emailin1:
        to_list.append(emailin1)
    if emailin2:
        to_list.append(emailin2)

    msg["To"] = ', '.join(to_list)

    from_dom = emailfrom.split('@')[1]
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=from_dom)
    msg["Subject"] = etitle

    # Reply threading headers
    if send_mode == 'reply' and original_message_id:
        msg['In-Reply-To'] = original_message_id
        if references:
            msg['References'] = f'{references} {original_message_id}'.strip()
        else:
            msg['References'] = original_message_id

    msg.attach(MIMEText(ebody, 'html'))

    # Final recipient list for SMTP
    emailto = []
    if emailin1:
        emailto.append(emailin1)
    if emailin2:
        emailto.append(emailin2)
    if emailcc1:
        emailto.append(emailcc1)
    if emailcc2:
        emailto.append(emailcc2)

    [host, port] = ourserver.split(':')
    port = int(port)

    try:
        t0 = time.perf_counter()
        server = smtplib.SMTP(host, port, timeout=20)
        print("SMTP connect:", time.perf_counter() - t0)
        print("Successfully connected to the SMTP server.")

        t0 = time.perf_counter()
        server.starttls(context=ssl.create_default_context())
        print("SMTP starttls:", time.perf_counter() - t0)
        print("Started TLS")

        t0 = time.perf_counter()
        server.login(username, password)
        print("SMTP login:", time.perf_counter() - t0)
        print("Server logged in")

        msg_as_string = msg.as_string()
        t0 = time.perf_counter()
        server.sendmail(emailfrom, emailto, msg_as_string)
        print("SMTP sendmail:", time.perf_counter() - t0)
        print("Sent the email")

        server.quit()

        # Save exact sent copy to IMAP Sent folder
        if save_sent and not is_zoho and not is_gmail:
            append_to_sent_folder(msg.as_bytes(), emailsender, sent_folder=sent_folder)
        else:
            if is_zoho:
                print("Skipping append_to_sent_folder (Zoho auto-saves Sent)")
            if is_gmail:
                print("Skipping append_to_sent_folder (Gmail auto-saves Sent)")


        return {
            'ok': True,
            'to': emailin1,
            'message_id': msg['Message-ID']
        }

    except smtplib.SMTPConnectError as e:
        print(f"SMTP connection error: {e}")
        print("Possible causes: Incorrect server address or port, firewall issues, server not reachable.")
    except socket.gaierror as e:
        print(f"Address resolution error: {e}")
        print("Possible causes: Incorrect hostname, no internet connection, DNS issues.")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP server disconnected prematurely: {e}")
        print("Possible causes: Server issues, connection timeout.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return {
        'ok': False,
        'to': emailin1,
        'message_id': None
    }
