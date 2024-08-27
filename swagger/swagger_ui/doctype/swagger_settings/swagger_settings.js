// Copyright (c) 2024, Omkar Darves and contributors
// For license information, please see license.txt

frappe.ui.form.on("Swagger Settings", "generate_swagger_json", function(frm) {
    frappe.call({
      method: "swagger.swagger_generator.generate_swagger_json",
    });
  });