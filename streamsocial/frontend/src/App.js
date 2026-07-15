import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState({
    totalEvents: 0,
    userRegistrations: 0,
    contentInteractions: 0
  });

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await axios.get('http://localhost:8000/events/recent');
      if (response.data.success) {
        const eventList = response.data.events;
        setEvents(eventList);
        
        const userRegs = eventList.filter(e => e.event_type === 'user_registration').length;
        const interactions = eventList.filter(e => 
          ['content_like', 'content_comment', 'content_share'].includes(e.event_type)
        ).length;
        
        setStats({
          totalEvents: eventList.length,
          userRegistrations: userRegs,
          contentInteractions: interactions
        });
      }
    } catch (error) {
      console.error('Error fetching events:', error);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>StreamSocial Event Dashboard</h1>
        <p>Real-time Event-Driven Architecture in Action</p>
      </header>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Events</h3>
          <div className="value">{stats.totalEvents}</div>
        </div>
        <div className="stat-card">
          <h3>User Registrations</h3>
          <div className="value">{stats.userRegistrations}</div>
        </div>
        <div className="stat-card">
          <h3>Content Interactions</h3>
          <div className="value">{stats.contentInteractions}</div>
        </div>
      </div>

      <div className="events-section">
        <h2>Recent Events</h2>
        {events.length > 0 ? (
          <div className="events-list">
            {events.map((event, index) => (
              <div key={index} className="event-item">
                <h4>{event.event_type || 'Unknown Event'}</h4>
                <p><strong>User ID:</strong> {event.user_id}</p>
                <p><strong>Event ID:</strong> {event.event_id}</p>
                {event.event_data && (
                  <p><strong>Data:</strong> {JSON.stringify(event.event_data)}</p>
                )}
                <small>Timestamp: {event.timestamp}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>No events yet. Generate some events to see them here!</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;