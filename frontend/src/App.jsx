import { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function App() {
  const [formData, setFormData] = useState({
    mark: 'TEAR, POUR, LIVE MORE',
    goods_services: 'Energy drinks, sports drinks, dietary supplements',
    classes: '5, 32',
    prior_marks: 'LIVEMORE, 5234567\nPOURMORE, 6123456'
  });
  
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    console.log('Form submitted!'); // Debug
    setLoading(true);
    setError(null);
    setAnalysis(null); // Clear previous results

    try {
      // Parse classes
      const classes = formData.classes
        .split(',')
        .map(c => parseInt(c.trim()))
        .filter(c => !isNaN(c));

      // Parse prior marks
      const prior_marks = formData.prior_marks.trim() 
        ? formData.prior_marks.split('\n').map(line => {
            const parts = line.split(',').map(s => s.trim());
            return { 
              name: parts[0] || '', 
              registration: parts[1] || '' 
            };
          }).filter(m => m.name)
        : [];

      console.log('Sending request...', { mark: formData.mark, classes, prior_marks }); // Debug

      const response = await axios.post(`${API_URL}/api/analyze`, {
        mark: formData.mark,
        goods_services: formData.goods_services,
        classes,
        prior_marks
      }, {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 120000 // 2 minutes timeout
      });

      console.log('Response received:', response.data); // Debug
      setAnalysis(response.data);
      
    } catch (err) {
      console.error('Error:', err); // Debug
      const errorMsg = err.response?.data?.detail 
        || err.message 
        || 'Failed to analyze trademark. Please check if the backend is running.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level) => {
    const colors = {
      critical: 'risk-critical',
      high: 'risk-high',
      moderate: 'risk-moderate',
      low: 'risk-low',
      minimal: 'risk-minimal'
    };
    return colors[level] || colors.moderate;
  };

  const getSeverityBadge = (severity) => {
    const badges = {
      critical: { bg: '#dc2626', text: '#fff' },
      high: { bg: '#ea580c', text: '#fff' },
      moderate: { bg: '#ca8a04', text: '#fff' },
      low: { bg: '#2563eb', text: '#fff' },
      minimal: { bg: '#16a34a', text: '#fff' }
    };
    return badges[severity] || badges.moderate;
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(to bottom right, #f8fafc, #e0f2fe)' }}>
      {/* Header */}
      <div className="header">
        <div className="container">
          <h1>Trademark Risk Assessment</h1>
          <p>AI-powered analysis with zero-hallucination citations</p>
        </div>
      </div>

      <main className="container">
        {/* Input Form */}
        <div className="card">
          <h2 style={{ fontSize: '20px', marginBottom: '20px' }}>Trademark Application Details</h2>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-2">
              <div>
                <label>Trademark</label>
                <input
                  type="text"
                  value={formData.mark}
                  onChange={(e) => setFormData({ ...formData, mark: e.target.value })}
                  required
                />
              </div>
              
              <div>
                <label>Classes (comma-separated)</label>
                <input
                  type="text"
                  value={formData.classes}
                  onChange={(e) => setFormData({ ...formData, classes: e.target.value })}
                  placeholder="e.g., 5, 32"
                  required
                />
              </div>
            </div>

            <div style={{ marginTop: '16px' }}>
              <label>Goods/Services</label>
              <textarea
                value={formData.goods_services}
                onChange={(e) => setFormData({ ...formData, goods_services: e.target.value })}
                rows="2"
                required
              />
            </div>

            <div style={{ marginTop: '16px' }}>
              <label>Prior Marks (optional, one per line: NAME, REGISTRATION)</label>
              <textarea
                value={formData.prior_marks}
                onChange={(e) => setFormData({ ...formData, prior_marks: e.target.value })}
                rows="3"
                placeholder="LIVEMORE, 5234567&#10;POURMORE, 6123456"
              />
            </div>

            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
              style={{ marginTop: '20px' }}
            >
              {loading ? 'Analyzing...' : 'Analyze Trademark'}
            </button>
          </form>

          {error && (
            <div className="error" style={{ marginTop: '16px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
            <h3>🔍 Analyzing Trademark...</h3>
            <p style={{ color: '#6b7280', marginTop: '8px' }}>
              This may take 30-60 seconds. Please wait...
            </p>
          </div>
        )}

        {/* Results */}
        {analysis && !loading && (
          <div>
            {/* Overall Risk Card */}
            <div className={`card ${getRiskColor(analysis.overall_risk_level || 'moderate')}`} style={{ marginBottom: '24px' }}>
              <h2 style={{ fontSize: '28px', textTransform: 'uppercase', marginBottom: '8px' }}>
                {(analysis.overall_risk_level || 'MODERATE').toUpperCase()} RISK
              </h2>
              <p style={{ fontSize: '16px' }}>
                Overall Score: {(analysis.overall_risk_score || 0).toFixed(1)}/100 | 
                Confidence: {((analysis.overall_confidence || 0) * 100).toFixed(1)}%
                {analysis.requires_human_review && ' ⚠️ Human Review Required'}
              </p>
            </div>

            {/* Risk Dimensions */}
            {(analysis.rejection_likelihood || analysis.overcoming_difficulty || analysis.legal_precedent_strength || analysis.examiner_discretion) && (
            <div className="card">
              <h3 style={{ fontSize: '18px', marginBottom: '20px' }}>Risk Dimensions</h3>
              <div className="grid grid-2">
                {[
                  { key: 'rejection_likelihood', data: analysis.rejection_likelihood, label: 'Rejection Likelihood' },
                  { key: 'overcoming_difficulty', data: analysis.overcoming_difficulty, label: 'Overcoming Difficulty' },
                  { key: 'legal_precedent_strength', data: analysis.legal_precedent_strength, label: 'Legal Precedent' },
                  { key: 'examiner_discretion', data: analysis.examiner_discretion, label: 'Examiner Discretion' }
                ].filter(dim => dim.data).map(({ key, data, label }) => (
                  <div key={key} style={{ padding: '16px', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <strong>{data.name || label}</strong>
                      <span style={{ fontSize: '24px', fontWeight: 'bold' }}>{(data.score || 0).toFixed(0)}</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: '#e5e7eb', borderRadius: '4px', marginBottom: '8px' }}>
                      <div 
                        style={{ 
                          width: `${data.score || 0}%`, 
                          height: '100%', 
                          background: '#3b82f6', 
                          borderRadius: '4px' 
                        }}
                      />
                    </div>
                    <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
                      Weight: {((data.weight || 0) * 100).toFixed(0)}% | Confidence: {((data.confidence || 0) * 100).toFixed(0)}%
                    </p>
                    <p style={{ fontSize: '14px', color: '#374151' }}>{data.explanation || ''}</p>
                  </div>
                ))}
              </div>
            </div>
            )}

            {/* Issues */}
            {analysis.issues && analysis.issues.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>
                Issues Identified ({analysis.issues.length})
              </h3>
              {analysis.issues.map((issue, idx) => {
                const badge = getSeverityBadge(issue.severity || 'moderate');
                return (
                  <div key={idx} className="issue-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                      <h4 style={{ fontSize: '16px', fontWeight: '600', flex: 1 }}>{issue.title || 'Issue'}</h4>
                      <span 
                        className="badge" 
                        style={{ 
                          background: badge.bg, 
                          color: badge.text,
                          marginLeft: '12px'
                        }}
                      >
                        {(issue.severity || 'moderate').toUpperCase()}
                      </span>
                    </div>
                    {issue.description && (
                      <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>
                        {issue.description}
                      </p>
                    )}
                    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>
                      <span>📄 TMEP §{issue.tmep_section || 'N/A'}</span>
                      <span>💰 {issue.estimated_cost || 'N/A'}</span>
                      <span>⏱️ {issue.estimated_time || 'N/A'}</span>
                    </div>
                    <div style={{ padding: '12px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '6px' }}>
                      <strong style={{ fontSize: '14px', color: '#1e40af' }}>Recommendation:</strong>
                      <p style={{ fontSize: '14px', color: '#1e40af', margin: '4px 0 0 0' }}>
                        {issue.recommendation || 'Consult with trademark attorney'}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
            )}

            {/* Recommendations */}
            {(analysis.primary_recommendation || analysis.alternative_strategies || analysis.estimated_total_cost) && (
            <div className="card">
              <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>Recommendations & Cost Estimate</h3>
              
              {analysis.primary_recommendation && (
              <div style={{ padding: '16px', background: 'linear-gradient(to right, #eff6ff, #eef2ff)', border: '1px solid #bfdbfe', borderRadius: '8px', marginBottom: '16px' }}>
                <p style={{ fontWeight: '600', marginBottom: '8px' }}>Primary Recommendation:</p>
                <p style={{ color: '#374151' }}>{analysis.primary_recommendation}</p>
              </div>
              )}

              <div className="grid grid-2" style={{ marginBottom: '16px' }}>
                {analysis.estimated_total_cost && (
                <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
                  <p style={{ fontWeight: '600', marginBottom: '8px' }}>💰 Estimated Cost</p>
                  <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#059669' }}>
                    {analysis.estimated_total_cost}
                  </p>
                </div>
                )}
                
                {analysis.estimated_timeline && (
                <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
                  <p style={{ fontWeight: '600', marginBottom: '8px' }}>⏱️ Estimated Timeline</p>
                  <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#2563eb' }}>
                    {analysis.estimated_timeline}
                  </p>
                </div>
                )}
              </div>

              {analysis.alternative_strategies && analysis.alternative_strategies.length > 0 && (
              <div>
                <p style={{ fontWeight: '600', marginBottom: '12px' }}>Alternative Strategies:</p>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {analysis.alternative_strategies.map((alt, idx) => (
                    <li key={idx} style={{ display: 'flex', alignItems: 'start', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ color: '#16a34a', fontSize: '20px' }}>✓</span>
                      <span style={{ color: '#374151' }}>{alt}</span>
                    </li>
                  ))}
                </ul>
              </div>
              )}
            </div>
            )}

            {/* Prior Marks Summary */}
            {analysis.prior_marks && analysis.prior_marks.total > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '18px', marginBottom: '16px' }}>Prior Marks Analysis</h3>
                <div className="grid grid-2">
                  <div style={{ textAlign: 'center', padding: '16px', background: '#f9fafb', borderRadius: '8px' }}>
                    <p style={{ fontSize: '32px', fontWeight: 'bold', color: '#111827' }}>
                      {analysis.prior_marks.total}
                    </p>
                    <p style={{ fontSize: '14px', color: '#6b7280' }}>Total Conflicts Found</p>
                  </div>
                  <div style={{ padding: '16px' }}>
                    <p style={{ marginBottom: '8px' }}>📋 USPTO: {analysis.prior_marks.uspto}</p>
                    <p style={{ marginBottom: '8px' }}>🏛️ State: {analysis.prior_marks.state}</p>
                    <p style={{ marginBottom: '8px' }}>⚖️ Common Law: {analysis.prior_marks.common_law}</p>
                    <p style={{ marginBottom: '8px' }}>🌐 Domains: {analysis.prior_marks.domains}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <div className="footer">
        <p>AI-Powered Trademark Risk Assessment System | Zero-Hallucination Citations | Confidence-Aware Analysis</p>
      </div>
    </div>
  );
}

export default App;
