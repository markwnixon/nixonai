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
from CCC_system_setup import websites, passwords, companydata, scac
from CCC_system_setup import usernames as em

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
