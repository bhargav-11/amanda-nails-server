from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Define the endpoint to get services
@app.route('/get_services', methods=['POST'])
def get_services():
    # Define the Belbo API endpoint and parameters
    belbo_api_url = 'https://amanda-nails.hairlist.ch/externalBooking/calcGroups'
    belbo_api_data = {
        'servicerGroupId': 423,
    }

    print("--- get services",  request.json)

    tool_call_id = request.json.get('message').get('toolCalls')[0].get('id')
    # Make a POST request to the Belbo API
    response = requests.post(belbo_api_url, data=belbo_api_data)
    # print(response.json())
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch services from Belbo API'}), response.status_code

    # Parse the response and extract the relevant attributes
    belbo_data = response.json()
    services = [
        {
            "id": service.get("id"),
            "description": service.get("description"),
            "fromPrice": service.get("fromPrice"),
            "maxPrice": service.get("maxPrice")
        }
        for service in belbo_data.get("services", [])
    ]

    # Format the response as specified
    result = {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": services
            }
        ]
    }

    return jsonify(result)

# Define the endpoint to get employees who can perform a particular service
@app.route('/get_employees', methods=['POST'])
def get_employees():
    # Extract necessary data from the request
    print("--- get employees",  request.json)
    request_data = request.json
    tool_call_id = request_data.get('message').get('toolCalls')[0].get('id')
    selected_products = request_data.get('message').get('toolCalls')[0].get("function").get('arguments').get('serviceIds')

    # Define the Belbo API endpoint and parameters
    belbo_api_url = 'https://amanda-nails.hairlist.ch/externalBooking/calcServicers'
    belbo_api_data = {
        'servicerGroupId': 423,
        'selectedProducts': ','.join(map(str, selected_products))
    }

    # Make a POST request to the Belbo API
    response = requests.post(belbo_api_url, data=belbo_api_data)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch employees from Belbo API'}), response.status_code

    # Parse the response and extract the relevant attributes
    belbo_data = response.json()
    group_to_servicers = belbo_data.get('groupToServicers', [])
    employees = []
    for group in group_to_servicers:
        for servicers in group.values():
            for servicer in servicers:
                employee_info = {
                    'id': servicer.get('id'),
                    'firstName': servicer.get('firstName'),
                    'role': servicer.get('role'),
                    'gender': servicer.get('gender', {}).get('name')
                }
                employees.append(employee_info)

    # Format the response as specified
    result = {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": employees
            }
        ]
    }

    return jsonify(result)

# Define the endpoint to get available slots on a particular date
@app.route('/get_available_slots', methods=['POST'])
def get_available_slots():
    # Extract necessary data from the request
    print("---  get_available_slots",  request.json)
    request_data = request.json
    tool_call_id = request_data.get('message').get('toolCalls')[0].get('id')
    arguments = request_data.get('message').get('toolCalls')[0].get("function").get('arguments')

    selected_products = arguments.get('serviceIds')  # List of service IDs
    date = arguments.get('date')  # Expected format: 'dd.MM.yyyy' (e.g., '02.01.2019')
    employee_id = arguments.get('employeeId', None)  # List of employee IDs; use [0] if any employee

    # Define the Belbo API endpoint and parameters
    belbo_api_url = 'https://amanda-nails.hairlist.ch/externalBooking/calcAvailableAppointments'
    belbo_api_data = {
        'servicerGroupId': 423,
        'selectedProducts': ','.join(map(str, selected_products)),
        'numberOfDays': 1,
        'offset': date,
    }

    belbo_api_data['bookingGroups[0]'] = employee_id

    # Make a POST request to the Belbo API
    response = requests.post(belbo_api_url, data=belbo_api_data)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch available slots from Belbo API'}), response.status_code

    # Parse the response and extract the relevant attributes
    belbo_data = response.json()
    general_availabilities = belbo_data.get('generalAvailabilities', {})
    available_slots = []
    for date_str, slots in general_availabilities.items():
        for slot in slots:
            slot_info = {
                'date': date_str,
                'time': slot.get('startDate'),
                'realDate': slot.get('realDate'),
                'servicers': slot.get('differentServicers'),
            }
            available_slots.append(slot_info)

    # Format the response as specified
    result = {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": available_slots
            }
        ]
    }

    return jsonify(result)

@app.route('/book_and_complete', methods=['POST'])
def book_and_complete():
    # Extract necessary data from the request
    print("--- get book_and_complete", request.json)
    request_data = request.json
    tool_call_id = request_data.get('message').get('toolCalls')[0].get('id')
    arguments = request_data.get('message').get('toolCalls')[0].get("function").get('arguments')

    date = arguments.get('date')
    time = arguments.get('time')
    selected_products = arguments.get('serviceIds')
    full_name = arguments.get('fullName')
    gender = arguments.get('gender')
    email = arguments.get('email')
    phone_number = request_data.get('message', {}).get('customer', {}).get('number', '1234567890')
    first_name = full_name.split()[0] if full_name else None
    last_name = full_name.split()[-1] if full_name else None
    servicer_group_id = 423
    employee_id = arguments.get('employeeId', 0)

    # Step 1: Start booking
    belbo_api_url_booking = 'https://amanda-nails.hairlist.ch/newAppointment/bookAppointment'
    belbo_api_data_booking = {
        'date': date,
        'time': time,
        'selectedProducts': ','.join(map(str, selected_products)),
        'servicerGroupId': servicer_group_id,
        'bookingSource': "Booked via AI Assistant",
    }
    belbo_api_data_booking['bookingGroups[0]'] = employee_id

    response_booking = requests.post(belbo_api_url_booking, data=belbo_api_data_booking)

    if response_booking.status_code != 200:
        return jsonify({'error': 'Appointment booking unsuccessful! Please try with another time slot'}), response_booking.status_code

    belbo_data_booking = response_booking.json()

    print("belbo_data_booking", belbo_data_booking)
    appointment_id = belbo_data_booking.get('appointmentId')
    appointment_participant_id = belbo_data_booking.get('appointmentParticipantId')

    if not appointment_id or not appointment_participant_id:
        return jsonify({'error': 'Appointment booking unsuccessful! Please try with another time slot'}), 400

    # Step 2: Add customer data
    belbo_api_url_customer_data = 'https://amanda-nails.hairlist.ch/externalBooking/persistCustomerData'
    belbo_api_data_customer = {
        'appointmentId': appointment_id,
        'genderType': gender,
        'firstName': first_name,
        'name': last_name,
        'mobile': phone_number,
        'email': email,
        'privacy': 'yes',
        'webBooking': 'yes',
        'terms': 'yes'
    }

    print("belbo_api_data_customer", belbo_api_data_customer)
    response_customer = requests.post(belbo_api_url_customer_data, data=belbo_api_data_customer)
    if response_customer.status_code != 200:

        print("response_customer", response_customer.json())
        return jsonify({'error': 'Failed to add customer data to booking', result: response_customer}), response_customer.status_code
    
    print("response_customer", response_customer.json())

    # Step 3: Finalize the booking
    belbo_api_url_finalize = 'https://amanda-nails.hairlist.ch/externalBooking/finalizeBooking'
    belbo_api_data_finalize = {
        'appointmentId': appointment_id,
        'appointmentParticipantId': appointment_participant_id,
    }
    response_finalize = requests.post(belbo_api_url_finalize, data=belbo_api_data_finalize)

    print("response_finalize", response_finalize.json())
    if response_finalize.status_code != 200:
        return jsonify({'error': 'Failed to finalize booking with Belbo API'}), response_finalize.status_code

    belbo_data_finalize = response_finalize.json()
    if belbo_data_finalize.get('result') != 'OK':
        return jsonify({'error': 'Failed to finalize booking', 'details': belbo_data_finalize}), 400

    # Combine results
    combined_result = {
        'booking': belbo_data_booking,
        'customer_data': response_customer.json(),
        'finalization': []
    }

    # Format the response
    result = {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": combined_result
            }
        ]
    }

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
