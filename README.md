# Google Compute Engine demo suite

## About

The Compute Engine demo suite contains a variety of demos showing how
to use Google Compute Engine. The demos are available live at
[http://gce-demos.appspot.com][1].

If you would like to run the application locally, follow the setup
instructions.

## Setup Instructions

1. Update the application value in the root `app.yaml` file to your own
   App Engine app identity.

        application: your-app-id

   More information about the app.yaml file can be found in the [App
   Engine documentation][2].

2. Add a `client_secrets.json` file within the `lib/google_cloud` directory
   with your client id and secrets, as found in the API console. The file
   should look something like this:

   <pre>{
     "web": {
       "client_id": "24043....apps.googleusercontent.com",
       "client_secret": "iPVXC5...xVz",
       "redirect_uris": ["http://localhost:8080/oauth2callback",
                         "http://&lt;your-app-id&gt;.appspot.com/oauth2callback"],
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://accounts.google.com/o/oauth2/token"
     }
   }</pre>

   Also make sure that the redirect URIs are correctly associated with the
   client id and secret in the API console.

   More information about client secrets can be found in the
   [API client library documentation][3].

3. (optional) Update any of the defaults in the settings.json to
   match your preferences.

4. (optional) You can optionally create custom images for the Fractal and
   Image Magick demos that will allow the instances to start quicker. First,
   start the instances using the demo UI. When at least one of the instances
   is up and running, ssh into that instance and follow the directions
   [here][7] for creating an image for an instance.

   Name the images `fractal-demo-image` and `image-magick-demo-image`
   respectively.

5. Install dependencies listed in the dependencies section into the `ext_lib`
   directory. You can do this easily by executing the
   `download_dependencies.sh` bash script. Beware that this will delete all
   current contents of the `ext_lib` dir and download the dependencies fresh.

## Dependencies

Add to `ext_lib` directory:

- [python_gflags-2.0][8]
- [httplib2-0.8][9]
- [oauth2client-1.0][10]
- [google-api-python-client][11]

When adding new dependencies do the following:

1. Add them to the list here
2. Add them to the `download_dependencies.sh` script.
3. Add them to `demo-suite/lib_path.py`

## Fractal Demo

### Load Balancing
The fractal demo can use load balancing.  However, the feature is in preview and the API is under active development.  As such, there are some pieces missing that will be filled in as the feature reaches maturity.

If load balancing **is** set up, it will work to forward all connections to an IP address to a set of VMs with a specific tag (fractal-cluster).  Currently, the projects that support this are hard coded in the `demo-suite/demos/fractal/main.py` along with the IP/hostnames for the load balancer.

### Boot from PD
If you initialize a set of boot PDs, they will be detected and used instead of booting from scratch disks.  Do do this run the `demo-suite/demos/fractal/createpds.sh` script.  You'll have to update it to point to your project.


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
