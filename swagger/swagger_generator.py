import ast
import importlib.util
import inspect
import json
import os
from typing import Literal

import frappe
from pydantic import BaseModel


def find_pydantic_model_in_decorator(node, type: Literal["request", "response"]):
    """Find the name of the Pydantic model used in the validate_request decorator.

    Args:
        node (ast.AST): The AST node representing the function definition.

    Returns:
        str: The name of the Pydantic model used in the decorator, if found.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.FunctionDef):
            for decorator in n.decorator_list:
                if isinstance(decorator, ast.Call):
                    if (
                        isinstance(decorator.func, ast.Name)
                        and decorator.func.id == f"validate_{type}"
                    ):
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Name):
                                return decorator.args[0].id
                            elif isinstance(decorator.args[0], ast.Attribute):
                                return f"{ast.dump(decorator.args[0].value)}.{decorator.args[0].attr}"
    return None


def get_pydantic_model_schema(model_name, module):
    """Extract the schema from a Pydantic model.

    Args:
        model_name (str): The name of the Pydantic model.
        module (module): The module where the model is defined.

    Returns:
        dict: The JSON schema of the Pydantic model, if valid.
    """
    if hasattr(module, model_name):
        model = getattr(module, model_name)
        if issubclass(model, BaseModel):
            return model.model_json_schema()
    return None


def process_function(app_name, module_name, func_name, func, swagger, module):
    """Process each function to update the Swagger paths.

    Args:
        app_name (str): The name of the app.
        module_name (str): The name of the module.
        func_name (str): The name of the function being processed.
        func (function): The function object.
        swagger (dict): The Swagger specification to be updated.
        module (module): The module where the function is defined.
    """
    try:
        source_code = inspect.getsource(func)
        tree = ast.parse(source_code)

        # Skip functions that do not contain validate_http_method calls
        if not any(
            "validate_http_method" in ast.dump(node) and isinstance(node, ast.Call)
            for node in ast.walk(tree)
        ):
            print(f"Skipping {func_name}: 'validate_http_method' not found")
            return

        # Find the Pydantic model used in the validate_request decorator
        pydantic_model_name = find_pydantic_model_in_decorator(tree, "request")
        pydantic_response_model_name = find_pydantic_model_in_decorator(
            tree, "response"
        )
        # Construct the API path for the function
        path = f"/api/method/{app_name}.api.{module_name}.{func_name}".lower()

        # Define the mapping of HTTP methods to check for in the source code
        http_methods = {
            "GET": "GET",
            "POST": "POST",
            "PUT": "PUT",
            "DELETE": "DELETE",
            "PATCH": "PATCH",
            "OPTIONS": "OPTIONS",
            "HEAD": "HEAD",
        }

        # Default HTTP method is POST
        http_method = "POST"
        for method in http_methods:
            if method in source_code:
                http_method = method
                break

        # Define the request body for methods that modify data
        request_body = {}
        if pydantic_model_name and http_method in ["POST", "PUT", "PATCH"]:
            pydantic_schema = get_pydantic_model_schema(pydantic_model_name, module)
            if pydantic_schema:
                request_body = {
                    "description": "Request body",
                    "required": True,
                    "content": {"application/json": {"schema": pydantic_schema}},
                }

        # Define query parameters for methods that retrieve data
        params = []
        if http_method in ["GET", "DELETE", "OPTIONS", "HEAD"]:
            signature = inspect.signature(func)
            for param_name, param in signature.parameters.items():
                if (
                    param.default is inspect.Parameter.empty
                    and not "kwargs" in param_name
                ):
                    param_type = "string"
                    params.append(
                        {
                            "name": param_name,
                            "in": "query",
                            "required": True,
                            "schema": {"type": param_type},
                        }
                    )
        if pydantic_response_model_name:
            pydantic_response_model = get_pydantic_model_schema(
                pydantic_response_model_name, module
            )
            responses = {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "status": {
                                        "type": "string",
                                        "enum": ["success", "error"],
                                    },
                                    "message": {"type": "string", "nullable": True},
                                    "data": pydantic_response_model,
                                }
                            }
                        }
                    },
                }
            }
        else:
            # Define the response schema
            responses = {
                "200": {
                    "description": "Successful response",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                }
            }

        # Assign tags for the Swagger documentation
        tags = [module_name]

        # Initialize the path if not already present
        if path not in swagger["paths"]:
            swagger["paths"][path] = {}

        # Update the Swagger specification with the function details
        swagger["paths"][path][http_method.lower()] = {
            "summary": func_name.title().replace("_", " "),
            "tags": tags,
            "parameters": params,
            "requestBody": request_body if request_body else None,
            "responses": responses,
            "security": [{"basicAuth": []}],
        }
    except Exception as e:
        # Log any errors that occur during processing
        frappe.log_error(
            f"Error processing function {func_name} in module {module_name}: {str(e)}"
        )


def load_module_from_file(file_path):
    """Load a module dynamically from a given file path.

    Args:
        file_path (str): The file path of the module.

    Returns:
        module: The loaded module.
    """
    module_name = os.path.basename(file_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@frappe.whitelist(allow_guest=True)
def generate_swagger_json():
    """Generate Swagger JSON documentation for all API methods.

    This function processes all Python files in the `api` directories of installed apps
    to generate a Swagger JSON file that describes the API methods.
    """
    swagger_settings = frappe.get_single("Swagger Settings")

    # Initialize the Swagger specification
    swagger = {
        "openapi": "3.0.0",
        "info": {
            "title": f"{swagger_settings.app_name} API",
            "version": "1.0.0",
        },
        "paths": {},
        "components": {},
    }

    # Add security schemes based on the settings in "Swagger Settings"
    if swagger_settings.token_based_basicauth or swagger_settings.bearerauth:
        swagger["components"]["securitySchemes"] = {}
        swagger["security"] = []

    if swagger_settings.token_based_basicauth:
        swagger["components"]["securitySchemes"]["basicAuth"] = {
            "type": "http",
            "scheme": "basic",
        }
        swagger["security"].append({"basicAuth": []})

    if swagger_settings.bearerauth:
        swagger["components"]["securitySchemes"]["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        swagger["security"].append({"bearerAuth": []})

    # Get the path to the Frappe bench directory
    frappe_bench_dir = frappe.utils.get_bench_path()
    file_paths = []

    # Gather all Python files in the `api` folders of each installed app
    for app in frappe.get_installed_apps():
        try:
            api_dir = os.path.join(frappe_bench_dir, "apps", app, app, "api")

            # Check if the `api` directory exists
            if os.path.exists(api_dir) and os.path.isdir(api_dir):
                # Walk through the `api` directory to gather all `.py` files
                for root, dirs, files in os.walk(api_dir):
                    for file in files:
                        if file.endswith(".py"):
                            file_paths.append((app, os.path.join(root, file)))
        except Exception as e:
            # Log any errors encountered while processing the app
            frappe.log_error(f"Error processing app '{app}': {str(e)}")
            continue

    # Process each Python file found
    for app, file_path in file_paths:
        try:
            if os.path.isfile(file_path) and app in str(file_path):
                module = load_module_from_file(file_path)
                module_name = os.path.basename(file_path).replace(".py", "")
                for func_name, func in inspect.getmembers(module, inspect.isfunction):
                    process_function(app, module_name, func_name, func, swagger, module)
            else:
                print(f"File not found: {file_path}")
        except Exception as e:
            frappe.log_error(f"Error loading or processing file {file_path}: {str(e)}")

    # Define the path to the Swagger JSON file
    www_dir = os.path.join(frappe_bench_dir, "apps", "swagger", "swagger", "www")

    # Ensure the www directory exists
    if not os.path.exists(www_dir):
        os.makedirs(www_dir)

    # Save the generated Swagger JSON to a file
    file_path = os.path.join(www_dir, "swagger.json")
    with open(file_path, "w") as swagger_file:
        json.dump(swagger, swagger_file, indent=4)

    frappe.msgprint("Swagger JSON generated successfully.")
