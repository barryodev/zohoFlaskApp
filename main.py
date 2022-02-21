from flask import Flask, render_template, request, session, flash, redirect, url_for

import requests
import json
import time

#init flask app object, setup instance based config
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config_google.py')

@app.route('/')
def root():
    """Root of flask app, renders a basic html page with links to app functionality

    Needs the Client id and redirect url passed in from config

    :return: Jinja2 template of front page of app
    """
    return render_template('index.html', client_id=app.config['ZOHO_CLIENT_ID'], redirect_url=app.config['REDIRECT_URL'])

@app.route('/zohoredirect')
def handleZohoAuthToken():
    """
    Once user has done authentication zoho will redirect them to return to this page

    Zoho will pass back an grant token that's valid for 2 minutes, you can use this grant token
    to get an access token that's valid for 1 hour, and a refresh token that can be used to
    generate more access tokens once they expire.

    :return: jinja template that handles the user returning from Zoho OAuth2 process
    """
    try:
        access_token = session['access_token']
        api_domain = session['api_domain']
        expiry_time = session['expiry_time']

        if (expiry_time - time.time()) <= 0:
            flash("Access token has expired")
            session.clear()
            return redirect('/')

    except KeyError:
        grant_token = request.args.get("code")
        accounts_URL = request.args.get("accounts-server")

        if grant_token is None or accounts_URL is None:
            flash("Tried to load redirect page without code or account url")
            return redirect('/')

        data = {'grant_type':'authorization_code',
            'client_id': app.config['ZOHO_CLIENT_ID'],
            'client_secret': app.config['ZOHO_SECRET'],
            'redirect_uri': app.config['REDIRECT_URL'],
            'code':grant_token}

        # This is the post request to zoho api the convert a grant token into an access token.
        r = requests.post(url=accounts_URL + '/oauth/v2/token', data=data)

        response_json = r.json()
        access_token = response_json['access_token']
        api_domain = response_json['api_domain']
        api_domain = api_domain.replace('www', 'sandbox')

        session['access_token'] = access_token
        session['api_domain'] = api_domain
        session['expiry_time'] = time.time() + 3540

        return render_template('zohoredirect.html')

    return render_template('zohoredirect.html')

@app.route('/viewcontacts')
def viewContacts():
    """This page handles making a get request to zoho for the first 200 contacts and
    then renders them through a jinja2 template.

    If the user's token is expired or missing, they'll be redirected to the root of app.

    :return: jinja template that displays all contacts returned from zoho
    """
    try:
        access_token = session['access_token']
        api_domain = session['api_domain']
        expiry_time = session['expiry_time']

        if (expiry_time - time.time()) <= 0:
            flash("Access token has expired")
            session.clear()
            return redirect('/')

    except KeyError:
        flash("Missing Zoho Authorisation")
        return redirect('/')

    headers = {'Authorization': "Zoho-oauthtoken " + access_token}
    parameters = {'fields': 'Phone,First_Name,Last_Name,Email',
                  'sort_order': 'asc',
                  'sort_by': 'Last_Name',
                  'page': '1',
                  'per_page': '200'}

    r = requests.get(url=api_domain + "/crm/v2/Contacts", headers=headers, params=parameters)

    contacts_json = r.json()
    contacts_list = contacts_json['data']

    return render_template('viewcontacts.html', contacts_list=contacts_list)

@app.route('/addcontact', methods=['GET', 'POST'])
def addContact():
    """Renders a html form to get contact details and then sends that to Zoho rest api with
    a post request.

    If the user's token is expired or missing, they'll be redirected to the root of app.

    :return: Jinja template that allows the user to add a contact to zoho
    """
    try:
        access_token = session['access_token']
        api_domain = session['api_domain']
        expiry_time = session['expiry_time']

        if (expiry_time - time.time()) <= 0:
            flash("Access token has expired")
            session.clear()
            return redirect('/')
    except KeyError:
        flash("Error: Missing Zoho Authorisation")
        return redirect('/')

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        email = request.form['email']

        error = None

        if not first_name:
            error = 'Error: First name is required.'
            flash(error)

        if not last_name:
            error = 'Error: Last name is required'
            flash(error)

        if not phone:
            error = 'Error: Phone is required'
            flash(error)

        if not email:
            error = 'Error: Email is required'
            flash(error)

        if error is None:
            headers = {'Authorization': "Zoho-oauthtoken " + access_token}
            request_body = dict()
            record_list = list()

            new_contact = {
                'First_Name': first_name,
                'Last_Name': last_name,
                'Phone': phone,
                'Email': email
            }

            record_list.append(new_contact)
            request_body['data'] = record_list

            trigger = [
                'approval',
                'workflow',
                'blueprint'
            ]

            request_body['trigger'] = trigger

            response = requests.post(url=api_domain + "/crm/v2/Contacts", headers=headers, data=json.dumps(request_body).encode('utf-8'))

            if response is not None:
                return redirect('/viewcontacts')


    return render_template('addcontact.html')

@app.route('/sessionclear')
def clearSession():
    """
    Simple page to clear the session, so you can run OAuth2 process again without waiting for it to expire
    :return:
    """
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    # This line allows us to run the app locally
    app.run(host='127.0.0.1', port=8080, debug=True)



