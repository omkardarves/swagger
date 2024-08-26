import ast
import importlib.util
import inspect
import json
import os

import frappe
from pydantic import BaseModel


def find_pydantic_model_in_decorator(node):
    """Find the name of the Pydantic model used in validate_request decorator."""
    for n in ast.walk(node):
        if isinstance(n, ast.FunctionDef):
            for decorator in n.decorator_list:
                if isinstance(decorator, ast.Call):
                    if (
                        isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "validate_request"
                    ):
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Name):
                                return decorator.args[0].id
                            elif isinstance(decorator.args[0], ast.Attribute):
                                return f"{ast.dump(decorator.args[0].value)}.{decorator.args[0].attr}"
    return None


def get_pydantic_model_schema(model_name, module):
    """Extract schema from Pydantic model."""
    if hasattr(module, model_name):
        model = getattr(module, model_name)
        if issubclass(model, BaseModel):
            return model.schema()
    return None


def process_function(app_name, module_name, func_name, func, swagger, module):
    """Process each function to update the Swagger paths."""
    try:
        source_code = inspect.getsource(func)
        tree = ast.parse(source_code)

        pydantic_model_name = find_pydantic_model_in_decorator(tree)

        path = f"/api/method/{app_name}.api.{module_name}.{func_name}".lower()

        # Define a mapping of HTTP methods to source code checks
        http_methods = {
            "GET": "GET",
            "POST": "POST",
            "PUT": "PUT",
            "DELETE": "DELETE",
            "PATCH": "PATCH",
            "OPTIONS": "OPTIONS",
            "HEAD": "HEAD",
        }

        http_method = "POST"  # Default to POST
        for method in http_methods:
            if method in source_code:
                http_method = method
                break

        request_body = {}
        if pydantic_model_name and http_method in ["POST", "PUT", "PATCH"]:
            pydantic_schema = get_pydantic_model_schema(pydantic_model_name, module)
            if pydantic_schema:
                request_body = {
                    "description": "Request body",
                    "required": True,
                    "content": {"application/json": {"schema": pydantic_schema}},
                }

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

        responses = {
            "200": {
                "description": "Successful response",
                "content": {"application/json": {"schema": {"type": "object"}}},
            }
        }

        tags = [module_name]

        if path not in swagger["paths"]:
            swagger["paths"][path] = {}

        swagger["paths"][path][http_method.lower()] = {
            "summary": func_name.title().replace("_", " "),
            "tags": tags,
            "parameters": params,
            "requestBody": request_body if request_body else None,
            "responses": responses,
            "security": [{"basicAuth": []}],
        }
    except Exception as e:
        frappe.log_error(
            f"Error processing function {func_name} in module {module_name}: {str(e)}"
        )


def load_module_from_file(file_path):
    """Load a module from a file path."""
    module_name = os.path.basename(file_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@frappe.whitelist(allow_guest=True)
def generate_swagger_json():
    """Generate Swagger JSON documentation."""
    swagger = {
        "openapi": "3.0.0",
        "info": {
            "title": "Frappe API",
            "version": "1.0.0",
        },
        "paths": {},
        "components": {
            "securitySchemes": {
                "basicAuth": {
                    "type": "http",
                    "scheme": "basic",
                }
            }
        },
        "security": [{"basicAuth": []}],
    }

    frappe_bench_dir = frappe.utils.get_bench_path()
    file_paths = []

    # Gather all Python files in the `api` folders of each installed app
    for app in frappe.get_installed_apps():
        try:
            # Construct the path to the `api` folder
            api_dir = os.path.join(frappe_bench_dir, "apps", app, app, "api")
            
            # Check if the `api` directory exists
            if os.path.exists(api_dir) and os.path.isdir(api_dir):
                # Walk through the `api` directory to gather all `.py` files
                for root, dirs, files in os.walk(api_dir):
                    for file in files:
                        if file.endswith(".py"):
                            file_paths.append(os.path.join(root, file))
        except Exception as e:
            # Log the error and continue with the next app
            frappe.log_error(f"Error processing app '{app}': {str(e)}")
            continue

    # Process each Python file found
    for file_path in file_paths:
        try:
            if os.path.isfile(file_path) and "jsk" in str(file_path):
                print(file_path,"file_pathfile_path")
                module = load_module_from_file(file_path)
                module_name = os.path.basename(file_path).replace(".py", "")
                for func_name, func in inspect.getmembers(module, inspect.isfunction):
                    print(func_name)
                    process_function("jsk",module_name, func_name, func, swagger, module)
            else:
                print(f"File not found: {file_path}")
        except Exception as e:
            frappe.log_error(f"Error loading or processing file {file_path}: {str(e)}")

    # Save the generated Swagger JSON to a file
    www_dir = os.path.join(frappe_bench_dir, "apps", "swagger", "swagger","www")

    # Ensure the www directory exists
    if not os.path.exists(www_dir):
        os.makedirs(www_dir)

    # Define the full path to the file to be written
    file_path = os.path.join(www_dir, "swagger.json")
    with open(file_path, "w") as swagger_file:
        json.dump(swagger, swagger_file, indent=4)

    frappe.msgprint("Swagger JSON generated successfully.")