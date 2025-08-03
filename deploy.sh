#!/bin/bash
# Deploy to Heroku and set required env vars
heroku git:remote -a YOUR_HEROKU_APP_NAME
heroku config:set MONGODB_URI=your_mongodb_uri
heroku config:set FIREBASE_API_KEY=your_firebase_api_key
heroku config:set FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
heroku config:set FIREBASE_PROJECT_ID=your_firebase_project_id
heroku config:set FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
heroku config:set FIREBASE_MESSAGING_SENDER_ID=your_firebase_messaging_sender_id
heroku config:set FIREBASE_APP_ID=your_firebase_app_id
heroku config:set FIREBASE_MEASUREMENT_ID=your_firebase_measurement_id
heroku config:set STRIPE_SECRET_KEY=your_stripe_secret_key
heroku config:set MAIL_USERNAME=your_mail_username
heroku config:set MAIL_PASSWORD=your_mail_password
heroku config:set FLASK_SECRET_KEY=your_flask_secret_key
git push heroku main
