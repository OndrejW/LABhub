# Security Notes

LABhub was originally built around a specific lab environment. Public or shared deployment requires cleaning up local assumptions.

## Secrets

The application reads deploy-time configuration from environment variables. Do not add secrets to source control.

## Data

SQLite databases that contain real users, logs, remarks, paths, or images are private operational data. They should not be committed to the public repository. Use private migration or import processes when historical data is required.

## Authentication And Registration

The app supports public self-registration at the route level. Deployers must decide whether that is acceptable, whether the app is network-restricted, and whether an approval/admin workflow is needed.

## Uploads

Uploaded images and files are stored under `labhub/static`. Production deployments should document allowed file types, maximum request size, malware scanning policy if needed, and backup coverage.

## External Services

Do not add external-service integrations until the data flow is approved for the deployment environment.
