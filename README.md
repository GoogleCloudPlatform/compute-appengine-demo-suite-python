# Google Compute Engine demo suite

## About

The Compute Engine demo suite contains a variety of demos showing how
to use Google Compute Engine. The demos are available live at
[http://gce-demos.appspot.com][1].

If you would like to run the application locally, follow the setup
instructions.

## Setup Instructions

1. Update the application value in the root app.yaml file to your own
   App Engine app identity.

   application: your-app-id

   More information about the app.yaml file can be found in the [App
   Engine documentation][2].

2. Add a client_secrets.json file within the lib/gc_appengine directory
   with your client id and secrets, as found in the API console. The file
   should look something like this:

   <pre>{
     "web": {
       "client_id": "24043....apps.googleusercontent.com",
       "client_secret": "iPVXC5...xVz",
       "redirect_uris": ["http://localhost:8080/oauth2callback",
                         "http://<your-app-id>.appspot.com/oauth2callback"],
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://accounts.google.com/o/oauth2/token"
     }
   }</pre>

   Also make sure that the redirect URIs are correctly associated with the
   client id and secret in the API console.

   More information about client secrets can be found in the
   [API client library documentation][3].

3. The Fractal demo requires addition of a Service email account to your
   project team members. The Service email account is of the format

   your-app-id@appspot.gserviceaccount.com

   Add this to your list of team members in the API console under the Team
   section.

   More information about Service accounts can be found in the
   [API client library documentation][4].

4. The Fractal demo also requires 2 files to be stored on [Cloud Storage][5].
   Create a bucket on Cloud Storage and upload the image_handler.py and
   mandelbrot.jar files found in demos/fractal/vm_files to that bucket.
   Change the path to the files in the Fractal Demo's startup.sh file to point
   to your Cloud Storage files.

5. Update the project value in the settings.json file with your own project id:

   "project": "your-project-id",

   Information on how to get your Compute Engine project ID can be found
   in the [Compute Engine documentation][6].

6. (optional) Update any of the other defaults in the settings.json to
   match your preferences.

7. (optional) You can optionally create custom images for the Fractal and
   Image Magick demos that will allow the instances to start quicker. First,
   start the instances using the demo UI. When at least one of the instances
   is up and running, ssh into that instance and follow the directions
   [here][7] for creating an image for an instance.

   Name the images 'fractal-demo-image' and 'image-magick-demo-image'
   respectively.

8. Install dependencies listed in the dependencies section.

## Dependencies

Add to /lib directory
- [python_gflags-2.0][8]
- [httplib2-0.7.7][9]
- [oauth2client-1.0][10]
- [google-api-python-client][11]


[1]: http://gce-demos.appspot.com
[2]: https://developers.google.com/appengine/docs/python/config/appconfig#About_app_yaml
[3]: https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
[4]: https://developers.google.com/api-client-library/python/platforms/google_app_engine#ServiceAccounts
[5]: https://developers.google.com/storage/
[6]: https://developers.google.com/compute/docs/faq#wherecanifind
[7]: https://developers.google.com/compute/docs/images#installinganimage
[8]: http://code.google.com/p/python-gflags/
[9]: http://code.google.com/p/httplib2/
[10]: http://pypi.python.org/pypi/oauth2client/1.0
[11]: https://code.google.com/p/google-api-python-client/
