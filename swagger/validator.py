from validator import validate as validate_
import frappe
import json
from functools import wraps
from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Literal, Optional, Generic
import swagger
from .responder import respond


def validate(data, rules):
    valid, valid_data, errors = validate_(data, rules, return_info=True)

    if not valid:
        from .exceptions import ValidationException

        raise ValidationException(errors=errors)

    return valid_data


def validate_http_method(*methods):
    if frappe.request:
        if frappe.request.method.upper() not in [method.upper() for method in methods]:
            from .exceptions import MethodNotAllowedException

            raise MethodNotAllowedException


def validate_request(model: Type[BaseModel]):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = json.loads(frappe.request.data)
                validated_data = model(**data)
                return func(validated_data)
            except ValidationError as e:
                swagger.log_api_error()
                return respond(
                    status=422, message="Validation error", errors=e.errors()
                )
            except Exception as e:
                swagger.log_api_error()
                return respond(status=422, message=str(e))

        wrapper._model = model
        return wrapper

    return decorator


def validate_response(model: Type[BaseModel]):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = func(*args, **kwargs)
                return respond(data=data)
            except ValidationError as e:
                swagger.log_api_error()
                return respond(
                    status=422, message="Validation error", errors=e.errors()
                )
            except Exception as e:
                swagger.log_api_error()
                return respond(status=500, message=str(e))

        wrapper._model = model
        return wrapper

    return decorator
