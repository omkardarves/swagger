import frappe
from .responder import respondNotFound

def __user(input=None):
    # get session user if input is not provided
    if not input:
        input = frappe.session.user
    res = frappe.get_all("User", or_filters={"email": input, "username": input})

    if len((res)) == 0:
        return "Guest"

    return frappe.get_doc("User", res[0].name).name


def log_api_error(mess=""):
    try:
        """
        Log API error to Error Log

        This method should be called before API responds the HTTP status code
        """

        # AI ALERT:
        # the title and message may be swapped
        # the better API for this is log_error(title, message), and used in many cases this way
        # this hack tries to be smart about whats a title (single line ;-)) and fixes it
        request_parameters = frappe.local.form_dict
        headers = {k: v for k, v in frappe.local.request.headers.items()}
        user_name = __user()

        if len(user_name) == 0:
            message = "Request Parameters : {}\n\nHeaders : {}".format(
                str(request_parameters), str(headers)
            )
        else:
            message = (
                "User Id : {}\n\nRequest Parameters : {}\n\nHeaders : {}".format(
                    str(user_name), str(request_parameters), str(headers)
                )
            )

        title = (
            request_parameters.get("cmd").split(".")[-1].replace("_", " ").title()
            + " API Error"
        )

        error = frappe.get_traceback() + "\n\n" + str(mess) + "\n\n" + message
        log = frappe.get_doc(
            dict(doctype="API Error Log", error=frappe.as_unicode(error), title=title)
        ).insert(ignore_permissions=True)
        frappe.db.commit()

        return log

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="API Error Log Error",
        )