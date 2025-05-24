# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import os
import socket
import threading

import xbmc

import syspath
import dbus_utils
import log
import oe


class Service_Thread(threading.Thread):

    SOCKET = '/var/run/service.libreelec.settings.sock'

    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = None # Ensure sock is initialized for cleanup in case init fails
        self.init()

    @log.log_function()
    def init(self):
        try:
            if os.path.exists(self.SOCKET):
                os.remove(self.SOCKET)
            self.daemon = True
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.setblocking(1) # Consider if non-blocking with select/poll is better for future
            self.sock.bind(self.SOCKET)
            self.sock.listen(5) # Changed backlog from 1 to 5
            self.stop_event = threading.Event()
        except socket.error as e:
            log.log(f"Service_Thread init error: {e}", log.ERROR)
            if self.sock:
                self.sock.close()
            # Depending on desired behavior, could re-raise or set an error flag
            raise # Or handle more gracefully if the service can run without the socket

    @log.log_function()
    def run(self):
        if oe.read_setting('libreelec', 'wizard_completed') == None:
            threading.Thread(target=oe.openWizard).start()

        while not self.stop_event.is_set():
            conn = None
            try:
                log.log(f'Waiting for connection', log.INFO)
                conn, addr = self.sock.accept()
                message = ""
                try:
                    data = conn.recv(1024)
                    if data:
                        message = data.decode('utf-8')
                    else:
                        # Client disconnected without sending data
                        log.log(f'Client disconnected before sending data', log.INFO)
                        continue # Skip processing for empty message
                except socket.error as e:
                    log.log(f"Error receiving data: {e}", log.ERROR)
                    continue # Skip processing this connection

                log.log(f'Received {message}', log.INFO)
                if message == 'openConfigurationWindow':
                    if not hasattr(oe, 'winOeMain') or not oe.winOeMain or oe.winOeMain.visible != True:
                        # Check oe.winOeMain existence as well
                        threading.Thread(target=oe.openConfigurationWindow).start()
                # Removed "exit" message handling here as stop_event is used
            except socket.error as e:
                if not self.stop_event.is_set(): # Avoid logging error if socket was closed by stop()
                    log.log(f"Socket accept error: {e}", log.ERROR)
                # If accept fails, and we are not stopping, either retry or break
                # For now, let's break if the main socket has issues, could also sleep and retry
                break
            except Exception as e: # Catch any other unexpected errors in the loop
                log.log(f"Unexpected error in Service_Thread run loop: {e}", log.ERROR)
            finally:
                if conn:
                    conn.close()
        log.log("Service_Thread run loop terminated.", log.INFO)

    @log.log_function()
    def stop(self):
        try:
            self.stop_event.set() # Signal the run loop to exit
            # Attempt to connect to the socket to unblock self.sock.accept()
            # This is a common pattern to make a blocking accept() return.
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.1) # Don't block indefinitely if socket is already gone
                try:
                    s.connect(self.SOCKET)
                    # No need to send "exit" anymore, the event handles termination.
                    # s.send(bytes('exit', 'utf-8')) # This was the old way
                except socket.error as e:
                    # This is expected if the server socket is already closing or closed
                    log.log(f"Socket error during stop (connect/send): {e}", log.DEBUG)

        except Exception as e:
            log.log(f"Error during Service_Thread stop initiation: {e}", log.ERROR)
        finally:
            self.join() # Wait for the run() method to complete
            if self.sock:
                self.sock.close()
            log.log("Service_Thread stopped.", log.INFO)


class Monitor(xbmc.Monitor):

    @log.log_function()
    def onScreensaverActivated(self):
        if oe.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.standby_devices).start()

    @log.log_function()
    def onDPMSActivated(self):
        if oe.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.standby_devices).start()

    @log.log_function()
    def run(self):
        service_thread = None
        try:
            dbus_utils.LOOP_THREAD.start()
            oe.load_modules()
            oe.start_service()
            service_thread = Service_Thread()
            service_thread.start()

            while not self.abortRequested():
                if self.waitForAbort(60): # Wait for 60 seconds or until abort is requested
                    break

                bt_standby_enabled = oe.read_setting('bluetooth', 'standby')
                if not bt_standby_enabled:
                    continue

                timeout_str = oe.read_setting('bluetooth', 'idle_timeout')
                if not timeout_str:
                    continue
                try:
                    timeout = int(timeout_str)
                except ValueError:
                    log.log(f"Invalid idle_timeout value: {timeout_str}", log.WARNING)
                    continue
                if timeout < 1:
                    continue
                if xbmc.getGlobalIdleTime() / 60 >= timeout:
                    log.log(f'Idle timeout reached for Bluetooth standby', log.DEBUG)
                    oe.standby_devices()
        finally:
            if hasattr(oe, 'winOeMain') and oe.winOeMain and hasattr(oe.winOeMain, 'visible'):
                 if oe.winOeMain.visible == True:
                    oe.winOeMain.close()
            
            oe.stop_service() # Ensure this is safe to call even if start_service partially failed
            
            if service_thread:
                service_thread.stop()
            
            # LOOP_THREAD should exist if start() was called.
            if hasattr(dbus_utils, 'LOOP_THREAD') and dbus_utils.LOOP_THREAD.is_alive():
                 dbus_utils.LOOP_THREAD.stop()

if __name__ == '__main__':
    Monitor().run()
