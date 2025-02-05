# NurtureIQ
A web app for tracking baby growth, with analytics and insights. I created this to track my own baby's data, instead of downloading an app. I run the web app off a Raspberry Pi on my home network, using a Postgres database. I've found hosting it over my local network to be useful not only for my household, but also for childcare professionals who come around and look after my child to use - all they have to do is connect to the Guest WiFi and navigate to the webapp URL.

# Installation
1. Clone the repo
2. Create your postgres database. I called mine nurture_iq.
3. Configure sqlalchemy_uri in the config.json file. This will be used to connect to the nurture_iq database that you've created.
4. Create venv and install requrements in requirements.txt.
5. Use flask to create the defined data model
```
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```
6. Test the app using ```python3 app.py```. Make sure the venv is activated, if you haven't done so already. Navigate to the site in your browser.
7. If all works as it should, then you can publish the app by installing/configuring gunicorn (or other WSGI HTTP server of your choice) and creating a service.

# Usage
The app is designed for quickly entering data, so that we can use that data for analysis later on. You'll land on the homepage. From there, you can navigate using the buttons to the subpages.
So your workflow will probably be adding data on the Add an Entry page, and viewing baby activity on the View Entries page. Once you have enough data, you'll be able to go to the analytics page for insights.