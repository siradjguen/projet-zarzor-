// src/components/AdminPanel.jsx - Fixed with Debug

import React, { useState, useEffect } from 'react';
import './AdminPanel.css';

const API_URL = 'http://localhost:8000/api';

const AdminPanel = () => {
  const [appointments, setAppointments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchPhone, setSearchPhone] = useState('');

  // Load appointments
  const loadAppointments = async () => {
    setIsLoading(true);
    setError(null);
    
    console.log('🔄 Loading appointments from:', `${API_URL}/appointments`);
    
    try {
      const response = await fetch(`${API_URL}/appointments`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('📡 Response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('📦 Data received:', data);

      if (data.success) {
        setAppointments(data.appointments || []);
        console.log(`✅ Loaded ${data.appointments?.length || 0} appointments`);
      } else {
        throw new Error(data.message || 'Failed to load appointments');
      }
    } catch (error) {
      console.error('❌ Error loading appointments:', error);
      setError(error.message);
      alert(`Error loading appointments: ${error.message}\n\nMake sure backend is running on port 8000`);
    } finally {
      setIsLoading(false);
    }
  };

  // Delete appointment
  const deleteAppointment = async (id) => {
    if (!window.confirm('Cancel this appointment?')) return;

    try {
      const response = await fetch(`${API_URL}/appointments/${id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        alert('✅ Appointment cancelled!');
        loadAppointments();
      } else {
        alert('❌ Failed to cancel: ' + data.message);
      }
    } catch (error) {
      console.error('Error deleting:', error);
      alert('Error cancelling appointment: ' + error.message);
    }
  };

  // Search by phone
  const searchByPhone = async () => {
    if (!searchPhone.trim()) {
      loadAppointments();
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/appointments/${searchPhone}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        setAppointments(data.appointments || []);
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      console.error('Error searching:', error);
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Cleanup old appointments
  const cleanupOld = async () => {
    if (!window.confirm('Remove all past appointments?')) return;

    try {
      const response = await fetch(`${API_URL}/appointments/cleanup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        alert('✅ Old appointments cleaned!');
        loadAppointments();
      }
    } catch (error) {
      console.error('Error cleaning:', error);
      alert('Error: ' + error.message);
    }
  };

  // Test backend connection
  const testConnection = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      const data = await response.json();
      console.log('🏥 Backend health:', data);
      alert(`✅ Backend is running!\n\nStatus: ${data.status}\nModel: ${data.groq?.model || 'N/A'}`);
    } catch (error) {
      console.error('❌ Backend not reachable:', error);
      alert('❌ Cannot connect to backend!\n\nMake sure:\n1. Backend is running (python run.py)\n2. It\'s on port 8000\n3. No firewall blocking');
    }
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  // Filter appointments
  const getFilteredAppointments = () => {
    if (!Array.isArray(appointments)) return [];

    const now = new Date();
    const today = now.toDateString();

    switch (filter) {
      case 'today':
        return appointments.filter(apt => {
          try {
            return new Date(apt.created_at).toDateString() === today;
          } catch {
            return false;
          }
        });
      case 'upcoming':
        return appointments.filter(apt => {
          try {
            return new Date(apt.created_at) >= now;
          } catch {
            return false;
          }
        });
      default:
        return appointments;
    }
  };

  const filtered = getFilteredAppointments();

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <div className="admin-title">
          <h1>🏥 Appointments Dashboard</h1>
          <p>Manage all medical appointments</p>
        </div>
        <div className="admin-stats">
          <div className="stat-card">
            <div className="stat-value">{appointments.length}</div>
            <div className="stat-label">Total</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{filtered.length}</div>
            <div className="stat-label">Filtered</div>
          </div>
        </div>
      </div>

      <div className="admin-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search by phone number..."
            value={searchPhone}
            onChange={(e) => setSearchPhone(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && searchByPhone()}
          />
          <button onClick={searchByPhone} className="btn-search">
            🔍 Search
          </button>
          <button onClick={loadAppointments} className="btn-reset">
            🔄 Reset
          </button>
        </div>

        <div className="filter-buttons">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === 'today' ? 'active' : ''}
            onClick={() => setFilter('today')}
          >
            Today
          </button>
          <button
            className={filter === 'upcoming' ? 'active' : ''}
            onClick={() => setFilter('upcoming')}
          >
            Upcoming
          </button>
        </div>

        <div className="action-buttons">
          <button onClick={loadAppointments} className="btn-refresh">
            ↻ Refresh
          </button>
          <button onClick={testConnection} className="btn-test">
            🔌 Test Backend
          </button>
          <button onClick={cleanupOld} className="btn-cleanup">
            🗑️ Cleanup Old
          </button>
        </div>
      </div>

      <div className="appointments-table">
        {error && (
          <div className="error-message">
            <p>❌ Error: {error}</p>
            <button onClick={testConnection} className="btn-test-inline">
              Test Backend Connection
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading appointments...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <p>📭 No appointments found</p>
            {appointments.length === 0 && (
              <div className="empty-hint">
                <p>Book an appointment in the chat to see it here!</p>
                <button onClick={testConnection} className="btn-test-inline">
                  Or Test Backend Connection
                </button>
              </div>
            )}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Patient</th>
                <th>Phone</th>
                <th>Date</th>
                <th>Time</th>
                <th>Duration</th>
                <th>Reason</th>
                <th>Doctor</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((apt) => (
                <tr key={apt.id}>
                  <td className="id-cell">{apt.id}</td>
                  <td className="name-cell">{apt.patient_name}</td>
                  <td className="phone-cell">{apt.patient_phone}</td>
                  <td>{apt.date}</td>
                  <td className="time-cell">{apt.time}</td>
                  <td>{apt.duration}</td>
                  <td>{apt.reason}</td>
                  <td>{apt.doctor}</td>
                  <td>
                    <span className={`status-badge ${apt.status}`}>
                      {apt.status}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => deleteAppointment(apt.id)}
                      className="btn-delete"
                      title="Cancel appointment"
                    >
                      ❌
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Debug Panel */}
      <div className="debug-panel">
        <details>
          <summary>🔧 Debug Info (click to expand)</summary>
          <div className="debug-content">
            <p><strong>API URL:</strong> {API_URL}</p>
            <p><strong>Appointments loaded:</strong> {appointments.length}</p>
            <p><strong>Filtered shown:</strong> {filtered.length}</p>
            <p><strong>Loading:</strong> {isLoading ? 'Yes' : 'No'}</p>
            <p><strong>Error:</strong> {error || 'None'}</p>
            <button onClick={testConnection} style={{marginTop: '10px'}}>
              Test Backend Now
            </button>
          </div>
        </details>
      </div>
    </div>
  );
};

export default AdminPanel;