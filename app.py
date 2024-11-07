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

# Define the endpoint to start and complete a booking
@app.route('/book_and_complete', methods=['POST'])
def book_and_complete():
    # Extract necessary data from the request
    print("--- get book_and_complete", request.json)
    request_data = request.json
    tool_call_id = request_data.get('message').get('toolCalls')[0].get('id')
    arguments = request_data.get('message').get('toolCalls')[0].get("function").get('arguments')

    date = arguments.get('date')  # Expected format: 'dd.MM.yyyy' (e.g., '02.01.2019')
    time = arguments.get('time')  # Expected format: 'HH:mm' (e.g., '16:00')
    selected_products = arguments.get('serviceIds')  # List of service IDs
    full_name = arguments.get('fullName')  # Full name of the customer
    phone_number = arguments.get('phoneNumber')  # Phone number of the customer
    servicer_group_id = 423  # As before
    booking_source = f"Name: {full_name}, Phone: {phone_number}, Booked via AI Assistant"
    success_page = None
    employee_id = arguments.get('employeeId', None)

    # Define the Belbo API endpoint and parameters for booking
    belbo_api_url_booking = 'https://amanda-nails.hairlist.ch/newAppointment/bookAppointment'
    belbo_api_data_booking = {
        'date': date,
        'time': time,
        'selectedProducts': ','.join(map(str, selected_products)),
        'servicerGroupId': servicer_group_id,
        'bookingSource': booking_source,
    }

    if success_page:
        belbo_api_data_booking['successPage'] = success_page

    belbo_api_data_booking['bookingGroups[0]'] = employee_id

    # Make a POST request to the Belbo API to start booking
    response_booking = requests.post(belbo_api_url_booking, data=belbo_api_data_booking)
    if response_booking.status_code != 200:
        print(f"Error starting booking: {response_booking.status_code} - {response_booking.text}")
        return jsonify({'error': 'Failed to start booking with Belbo API'}), response_booking.status_code

    # Parse the response
    belbo_data_booking = response_booking.json()

    # Handle possible 'GIVEN' result
    if belbo_data_booking.get('result') == 'GIVEN':
        print("Error: Time slot is already booked.")
        return jsonify({'error': 'Time slot is already booked'}), 400

    # Extract appointmentId and appointmentParticipantId
    appointment_id = belbo_data_booking.get('appointmentId')
    appointment_participant_id = belbo_data_booking.get('appointmentParticipantId')

    if not appointment_id or not appointment_participant_id:
        print("Error: Failed to retrieve appointment IDs from Belbo API.")
        print(f"Response data: {belbo_data_booking}")
        return jsonify({'error': 'Failed to retrieve appointment IDs from Belbo API'}), 400

    # Now, finalize the booking
    belbo_api_url_finalize = 'https://amanda-nails.hairlist.ch/externalBooking/finalizeBooking'
    belbo_api_data_finalize = {
        'appointmentId': appointment_id,
        'appointmentParticipantId': appointment_participant_id,
    }

    # Make a POST request to the Belbo API to finalize booking
    response_finalize = requests.post(belbo_api_url_finalize, data=belbo_api_data_finalize)
    if response_finalize.status_code != 200:
        print(f"Error finalizing booking: {response_finalize.status_code} - {response_finalize.text}")
        return jsonify({'error': 'Failed to finalize booking with Belbo API'}), response_finalize.status_code

    # Parse the response
    belbo_data_finalize = response_finalize.json()

    # Check for 'result' in response
    if belbo_data_finalize.get('result') != 'OK':
        print("Error: Failed to finalize booking.")
        print(f"Response data: {belbo_data_finalize}")
        return jsonify({'error': 'Failed to finalize booking', 'details': belbo_data_finalize}), 400

    # Combine the booking and finalize responses
    combined_result = {
        'booking': belbo_data_booking,
        'finalization': belbo_data_finalize
    }

    # Format the response as specified
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
