## Swagger UI

Dynamic Swagger UI for frappe Apps

#### License

mit


# Swagger Generator for Frappe Apps

This project provides a Swagger UI generator for Frappe apps, allowing developers to easily document and explore their APIs.

## Features

- **Automatic Swagger UI Generation**: Generates Swagger documentation for all API endpoints defined in your Frappe app.
- **Customizable**: Designed to work with APIs defined in the `api` folder of each installed Frappe app.
- **Pydantic Model Integration**: Automatically extracts and displays request bodies for APIs using Pydantic models.

## Setup Instructions

1. **API Location**: 
   - Ensure that your API functions are located in the `app_name/api` folder of your Frappe app. The generator fetches API endpoints from this directory.

2. **Generating Swagger JSON**:
   - Navigate to the "Swagger Settings" doctype within your Frappe app.
   - Click the "Generate Swagger JSON" button. This will create the `swagger.json` file, which contains all the necessary documentation for your API endpoints.

3. **Swagger UI**:
   - The Swagger UI will be automatically generated and accessible from the `swagger.html` file, allowing you to interact with and explore your API.

## Customization and Automation

While this generator offers a straightforward way to document APIs, further customization and automation are possible. Consider modifying the generator script to include additional features or automate certain steps as needed.

## Contributing

Contributions to this project are welcome. If you encounter issues or have ideas for improvements, feel free to open an issue or submit a pull request.

## License

This project is licensed under the terms specified in the `license.txt` file.
