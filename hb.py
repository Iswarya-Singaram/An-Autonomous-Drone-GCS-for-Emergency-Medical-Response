from pymavlink import mavutil

# Connect to the Pixhawk on serial0 at 57600 baud
the_connection = mavutil.mavlink_connection('/dev/ttyAMA0', baud=57600)

print("Waiting for heartbeat...")
the_connection.wait_heartbeat()
print("Heartbeat received from system (system %u component %u)" % (the_connection.target_system, the_connection.target_component))
