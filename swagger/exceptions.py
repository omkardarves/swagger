import frappe
from .responder import respond

class APIException(Exception):
	"""
	Base Exception for API Requests

	Usage:
	try:
		...
	except APIException as e:
		return e.respond()
	"""

	http_status_code = 500
	message = frappe._('Something went wrong')
	save_error_log = True
	errors = {}
	
	def __init__(self, message=None, errors=None):
		if message:
			self.message = message
		if errors:
			self.errors = errors

	def respond(self):
		if self.save_error_log:
			frappe.log_error()
		return respond(status=self.http_status_code, message=self.message, errors=self.errors)

class MethodNotAllowedException(APIException):
	http_status_code = 405
	message = frappe._('Method not allowed')
	save_error_log = False


class ValidationException(APIException):
	http_status_code = 422
	message = frappe._('Validation Error')
	save_error_log = False

	def __init__(self, errors, data=None):
		errors_ = dict()
		for key in errors.keys():
			# getting first error message
			errors_[key] = list(errors[key].values())[0]
		self.errors = errors_
		self.data = data

class NotFoundException(APIException):
	http_status_code = 404
	message = frappe._("Data not found")
	save_error_log = False


class ForbiddenException(APIException):
	http_status_code = 403
	message = frappe._("Please check the entered data")
	save_error_log = False


class UnauthorizedException(APIException):
	http_status_code = 401
	message = frappe._("Data expired")
	save_error_log = False


class FailureException(APIException):
	http_status_code = 422
	message = frappe._("Something went wrong")
	save_error_log = False


class RespondFailureException(APIException):
	http_status_code = 417
	message = frappe._("Something went wrong")
	save_error_log = False


class RespondWithFailureException(APIException):
	http_status_code = 500
	message = frappe._("Something went wrong")
	save_error_log = False

class InvalidUserTokenException(APIException):
	http_status_code = 401
	save_error_log = False

	def __init__(self, message):
		self.message = message