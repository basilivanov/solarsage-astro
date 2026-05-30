// AI_HEADER
// module: M-WEB-PROFILE-PAGE
// wave: W-2.6
// purpose: Profile page (view/edit)

'use client';

import { useState } from 'react';

export default function ProfilePage() {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    birthDate: '1990-01-15',
    birthTime: '14:30',
  });

  // TODO: fetch profile from /api/profile

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: POST /api/profile
    console.log('Saving profile:', formData);
    setEditing(false);
  };

  const handleLogout = () => {
    // TODO: implement logout
    console.log('Logging out...');
  };

  return (
    <div className="profile-page" data-testid="profile-page">
      <h1>Профиль</h1>

      {editing ? (
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="birthDate">Дата рождения</label>
            <input
              id="birthDate"
              type="date"
              value={formData.birthDate}
              onChange={(e) => setFormData({...formData, birthDate: e.target.value})}
              data-testid="birth-date-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="birthTime">Время рождения</label>
            <input
              id="birthTime"
              type="time"
              value={formData.birthTime}
              onChange={(e) => setFormData({...formData, birthTime: e.target.value})}
              data-testid="birth-time-input"
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="btn-primary" data-testid="save-button">
              Сохранить
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setEditing(false)}
              data-testid="cancel-button"
            >
              Отмена
            </button>
          </div>
        </form>
      ) : (
        <div className="profile-view">
          <div className="profile-field">
            <span className="field-label">Дата рождения:</span>
            <span className="field-value" data-testid="birth-date-display">
              {formData.birthDate}
            </span>
          </div>

          <div className="profile-field">
            <span className="field-label">Время рождения:</span>
            <span className="field-value" data-testid="birth-time-display">
              {formData.birthTime}
            </span>
          </div>

          <div className="profile-actions">
            <button
              className="btn-primary"
              onClick={() => setEditing(true)}
              data-testid="edit-button"
            >
              Редактировать
            </button>
            <button
              className="btn-danger"
              onClick={handleLogout}
              data-testid="logout-button"
            >
              Выйти
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
