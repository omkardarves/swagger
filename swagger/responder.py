import frappe
from frappe.auth import CookieManager

def respond(status=200, message='Success', data={}, errors={}):
	response = frappe._dict({'message': frappe._(message)})
	if data:
		response['data'] = data
	if errors:
		response['errors'] = errors
	frappe.local.response = response
	frappe.local.response['http_status_code'] = status

	frappe.local.cookie_manager = CookieManager()
	frappe.local.cookie_manager.flush_cookies(response=frappe.local.response)
	# return Response(response=json.dumps(response), status=status, content_type='application/json')

def respondWithSuccess(status=200, message='Success', data={}):
	return respond(status=status, message=message, data=data)

def respondWithFailure(status=500, message='Something went wrong', data={}, errors={}):
	return respond(status=status, message=message, data=data, errors=errors)

def respondUnauthorized(status=401, message='Unauthorized'):
	return respond(status=status, message=message)

def respondForbidden(status=403, message='Forbidden'):
	return respond(status=status, message=message)

def respondNotFound(status=404, message='Not Found'):
	return respond(status=status, message=message)
