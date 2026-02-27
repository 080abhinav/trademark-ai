import { useState, useRef } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function App() {
  // Input mode: 'form' or 'pdf'
  const [inputMode, setInputMode] = useState('form');

  const [formData, setFormData] = useState({
    mark: 'TEAR, POUR, LIVE MORE',
    goods_services: 'Energy drinks, sports drinks, dietary supplements',
    classes: '5, 32',
    prior_marks: 'LIVEMORE, 5234567\nPOURMORE, 6123456'
  });

  // PDF upload state
  const [pdfFile, setPdfFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Track which per-mark cards are expanded
  const [expandedMarks, setExpandedMarks] = useState({});
  // Whether the entire per-mark section is shown (collapsed by default)
  const [showPerMarkSection, setShowPerMarkSection] = useState(false);

  // --- Form submission ---
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    setLoading(true);
    setError(null);
    setAnalysis(null);

    try {
      const classes = formData.classes
        .split(',')
        .map(c => parseInt(c.trim()))
        .filter(c => !isNaN(c));

      const prior_marks = formData.prior_marks.trim()
        ? formData.prior_marks.split('\n').map(line => {
          const parts = line.split(',').map(s => s.trim());
          return {
            name: parts[0] || '',
            registration: parts[1] || ''
          };
        }).filter(m => m.name)
        : [];

      const response = await axios.post(`${API_URL}/api/analyze`, {
        mark: formData.mark,
        goods_services: formData.goods_services,
        classes,
        prior_marks
      }, {
        headers: { 'Content-Type': 'application/json' },
        timeout: 300000
      });

      setAnalysis(response.data);

    } catch (err) {
      const errorMsg = err.response?.data?.detail
        || err.message
        || 'Failed to analyze trademark. Please check if the backend is running.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // --- PDF upload & analysis ---
  const handlePdfSubmit = async () => {
    if (!pdfFile) {
      setError('Please select a PDF file first.');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis(null);

    try {
      const formPayload = new FormData();
      formPayload.append('file', pdfFile);

      const response = await axios.post(`${API_URL}/api/analyze-pdf`, formPayload, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 600000 // 10 minutes for large PDFs with many prior marks
      });

      setAnalysis(response.data);

    } catch (err) {
      const errorMsg = err.response?.data?.detail
        || err.message
        || 'Failed to analyze PDF. Please check if the backend is running.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // --- Drag & drop handlers ---
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      setError(null);
    } else {
      setError('Please drop a valid PDF file.');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setPdfFile(file);
      setError(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // --- Helpers ---
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

  const getConfusionBadge = (risk) => {
    const badges = {
      HIGH: { bg: '#dc2626', text: '#fff', border: '#fca5a5' },
      MEDIUM: { bg: '#f59e0b', text: '#111', border: '#fcd34d' },
      LOW: { bg: '#16a34a', text: '#fff', border: '#86efac' },
    };
    return badges[risk] || badges.MEDIUM;
  };

  const toggleMarkExpanded = (idx) => {
    setExpandedMarks(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(to bottom right, #f8fafc, #e0f2fe)' }}>
      {/* Header */}
      <div className="header">
        <div className="container">
          <h1>Trademark Risk Assessment</h1>
          <p>Anti-hallucination AI — per-mark analysis with validated TMEP citations</p>
        </div>
      </div>

      <main className="container">
        {/* Input Card */}
        <div className="card">
          <h2 style={{ fontSize: '20px', marginBottom: '20px' }}>Trademark Application Details</h2>

          {/* Input Mode Toggle */}
          <div className="input-mode-toggle">
            <button
              className={`toggle-btn ${inputMode === 'form' ? 'active' : ''}`}
              onClick={() => setInputMode('form')}
              type="button"
            >
              Manual Entry
            </button>
            <button
              className={`toggle-btn ${inputMode === 'pdf' ? 'active' : ''}`}
              onClick={() => setInputMode('pdf')}
              type="button"
            >
              Upload PDF Report
            </button>
          </div>

          {/* Form Mode */}
          {inputMode === 'form' && (
            <form onSubmit={handleFormSubmit}>
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
          )}

          {/* PDF Upload Mode */}
          {inputMode === 'pdf' && (
            <div>
              <div
                className={`upload-zone ${isDragging ? 'dragging' : ''} ${pdfFile ? 'has-file' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />

                {pdfFile ? (
                  <div className="file-preview">
                    <div className="file-icon">PDF</div>
                    <div className="file-info">
                      <p className="file-name">{pdfFile.name}</p>
                      <p className="file-size">{formatFileSize(pdfFile.size)}</p>
                    </div>
                    <button
                      className="file-remove"
                      onClick={(e) => { e.stopPropagation(); setPdfFile(null); }}
                      type="button"
                    >
                      X
                    </button>
                  </div>
                ) : (
                  <div className="upload-placeholder">
                    <div className="upload-icon">Upload</div>
                    <p className="upload-text">
                      <strong>Drop your PDF report here</strong> or click to browse
                    </p>
                    <p className="upload-hint">
                      Supports CompuMark reports, USPTO TESS reports, and similar trademark search documents
                    </p>
                  </div>
                )}
              </div>

              <button
                type="button"
                className="btn-primary"
                disabled={loading || !pdfFile}
                style={{ marginTop: '20px' }}
                onClick={handlePdfSubmit}
              >
                {loading ? 'Analyzing PDF...' : 'Analyze PDF Report'}
              </button>
            </div>
          )}

          {error && (
            <div className="error" style={{ marginTop: '16px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
            <h3>{inputMode === 'pdf' ? 'Parsing & Analyzing PDF...' : 'Analyzing Trademark...'}</h3>
            <p style={{ color: '#6b7280', marginTop: '8px' }}>
              {inputMode === 'pdf'
                ? 'Extracting data and analyzing each prior mark individually. This may take a few minutes for large reports...'
                : 'Analyzing each prior mark individually against TMEP guidelines. Please wait...'}
            </p>
            <p style={{ color: '#9ca3af', marginTop: '12px', fontSize: '13px' }}>
              Anti-hallucination: each prior mark is analyzed separately with focused TMEP context
            </p>
          </div>
        )}

        {/* Parsed PDF Preview */}
        {analysis && !loading && analysis.input_mode === 'pdf' && (
          <div className="card parsed-preview">
            <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#059669' }}>
              Extracted from PDF
            </h3>
            <div className="grid grid-2" style={{ gap: '12px' }}>
              <div className="parsed-item">
                <span className="parsed-label">Trademark</span>
                <span className="parsed-value">{analysis.parsed_mark}</span>
              </div>
              <div className="parsed-item">
                <span className="parsed-label">Classes</span>
                <span className="parsed-value">{(analysis.parsed_classes || []).join(', ') || 'N/A'}</span>
              </div>
              <div className="parsed-item">
                <span className="parsed-label">Goods/Services</span>
                <span className="parsed-value">{analysis.parsed_goods_services}</span>
              </div>
              <div className="parsed-item">
                <span className="parsed-label">Conflicts Found</span>
                <span className="parsed-value">{analysis.total_pdf_conflicts} total</span>
              </div>
            </div>
          </div>
        )}

        {/* ====== RESULTS ====== */}
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
                {analysis.requires_human_review && ' | Human Review Required'}
              </p>
            </div>

            {/* ====== PER-MARK BREAKDOWN (NEW — anti-hallucination feature) ====== */}
            {analysis.per_mark_results && analysis.per_mark_results.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '18px', marginBottom: '8px' }}>
                  Per-Mark Confusion Analysis
                </h3>
                <p style={{ fontSize: '13px', color: '#6b7280', marginBottom: '16px' }}>
                  Each prior mark analyzed individually against TMEP guidelines — prevents LLM overfeeding and hallucination
                </p>

                {/* Summary stats */}
                <div className="grid grid-3" style={{ gap: '12px', marginBottom: '20px' }}>
                  <div style={{
                    textAlign: 'center', padding: '14px',
                    background: analysis.high_risk_count > 0 ? '#fef2f2' : '#f0fdf4',
                    borderRadius: '8px',
                    border: `1px solid ${analysis.high_risk_count > 0 ? '#fca5a5' : '#bbf7d0'}`
                  }}>
                    <p style={{ fontSize: '28px', fontWeight: 'bold', color: '#dc2626' }}>
                      {analysis.high_risk_count || 0}
                    </p>
                    <p style={{ fontSize: '13px', color: '#6b7280' }}>HIGH Risk</p>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '14px', background: '#fffbeb',
                    borderRadius: '8px', border: '1px solid #fcd34d'
                  }}>
                    <p style={{ fontSize: '28px', fontWeight: 'bold', color: '#f59e0b' }}>
                      {analysis.medium_risk_count || 0}
                    </p>
                    <p style={{ fontSize: '13px', color: '#6b7280' }}>MEDIUM Risk</p>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '14px', background: '#f0fdf4',
                    borderRadius: '8px', border: '1px solid #bbf7d0'
                  }}>
                    <p style={{ fontSize: '28px', fontWeight: 'bold', color: '#16a34a' }}>
                      {analysis.low_risk_count || 0}
                    </p>
                    <p style={{ fontSize: '13px', color: '#6b7280' }}>LOW Risk</p>
                  </div>
                </div>

                {/* Toggle button to show/hide individual marks */}
                <button
                  onClick={() => setShowPerMarkSection(!showPerMarkSection)}
                  style={{
                    width: '100%', padding: '12px 16px',
                    background: showPerMarkSection ? '#f3f4f6' : 'linear-gradient(135deg, #eff6ff, #f0f9ff)',
                    border: '1px solid #d1d5db', borderRadius: '8px',
                    cursor: 'pointer', fontSize: '14px', fontWeight: '600',
                    color: '#374151', display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: showPerMarkSection ? '14px' : '0',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <span>
                    {showPerMarkSection ? 'Hide' : 'Show'} {analysis.per_mark_results.length} Individual Mark Results
                  </span>
                  <span style={{ fontSize: '12px', color: '#6b7280' }}>
                    {showPerMarkSection ? '▲ Collapse' : '▼ Expand'}
                  </span>
                </button>

                {/* Individual mark cards (only shown when expanded) */}
                {showPerMarkSection && analysis.per_mark_results.map((mark, idx) => {
                  const badge = getConfusionBadge(mark.confusion_risk);
                  const isExpanded = expandedMarks[idx];
                  return (
                    <div
                      key={idx}
                      style={{
                        marginBottom: '10px',
                        border: `1px solid ${badge.border}`,
                        borderRadius: '8px',
                        overflow: 'hidden',
                        background: '#fff',
                      }}
                    >
                      {/* Header row (always visible) */}
                      <div
                        onClick={() => toggleMarkExpanded(idx)}
                        style={{
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          padding: '12px 16px', cursor: 'pointer',
                          background: mark.confusion_risk === 'HIGH' ? '#fef2f2'
                            : mark.confusion_risk === 'MEDIUM' ? '#fffbeb' : '#f0fdf4'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                          <span
                            style={{
                              background: badge.bg, color: badge.text,
                              padding: '3px 10px', borderRadius: '12px',
                              fontSize: '12px', fontWeight: '700', whiteSpace: 'nowrap'
                            }}
                          >
                            {mark.confusion_risk}
                          </span>
                          <span style={{ fontWeight: '600', fontSize: '15px' }}>
                            {mark.prior_mark_name}
                          </span>
                          {mark.name_contained && (
                            <span style={{
                              background: '#fee2e2', color: '#dc2626',
                              padding: '2px 8px', borderRadius: '8px',
                              fontSize: '11px', fontWeight: '600'
                            }}>
                              NAME CONTAINED
                            </span>
                          )}
                          {mark.prior_mark_reg_number && (
                            <span style={{ color: '#9ca3af', fontSize: '12px' }}>
                              Reg. {mark.prior_mark_reg_number}
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '12px', color: '#6b7280' }}>
                            {(mark.confidence * 100).toFixed(0)}% conf.
                          </span>
                          <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                            {isExpanded ? '\u25B2' : '\u25BC'}
                          </span>
                        </div>
                      </div>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div style={{ padding: '14px 16px', borderTop: '1px solid #e5e7eb' }}>
                          <div className="grid grid-2" style={{ gap: '8px', marginBottom: '10px' }}>
                            <div>
                              <span style={{ fontSize: '12px', color: '#6b7280' }}>Prior Goods:</span>
                              <p style={{ fontSize: '13px' }}>{mark.prior_mark_goods || 'N/A'}</p>
                            </div>
                            <div>
                              <span style={{ fontSize: '12px', color: '#6b7280' }}>Prior Classes:</span>
                              <p style={{ fontSize: '13px' }}>
                                {mark.prior_mark_classes?.length > 0 ? mark.prior_mark_classes.join(', ') : 'N/A'}
                              </p>
                            </div>
                            <div>
                              <span style={{ fontSize: '12px', color: '#6b7280' }}>Mark Similar:</span>
                              <p style={{ fontSize: '13px' }}>{mark.is_similar ? 'Yes' : 'No'}</p>
                            </div>
                            <div>
                              <span style={{ fontSize: '12px', color: '#6b7280' }}>Goods Related:</span>
                              <p style={{ fontSize: '13px' }}>{mark.is_related_goods ? 'Yes' : 'No'}</p>
                            </div>
                          </div>
                          <div style={{ marginBottom: '8px' }}>
                            <span style={{ fontSize: '12px', color: '#6b7280' }}>Reasoning:</span>
                            <p style={{ fontSize: '13px', lineHeight: '1.5' }}>{mark.reasoning}</p>
                          </div>
                          <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#6b7280' }}>
                            <span>TMEP: {mark.tmep_section}</span>
                            <span>Key Factor: {mark.key_factor}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

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
                        <span>TMEP: {issue.tmep_section || 'N/A'}</span>
                        <span>Cost: {issue.estimated_cost || 'N/A'}</span>
                        <span>Timeline: {issue.estimated_time || 'N/A'}</span>
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
                      <p style={{ fontWeight: '600', marginBottom: '8px' }}>Estimated Cost</p>
                      <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#059669' }}>
                        {analysis.estimated_total_cost}
                      </p>
                    </div>
                  )}

                  {analysis.estimated_timeline && (
                    <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
                      <p style={{ fontWeight: '600', marginBottom: '8px' }}>Estimated Timeline</p>
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
                          <span style={{ color: '#16a34a', fontSize: '20px' }}>&#10003;</span>
                          <span style={{ color: '#374151' }}>{alt}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <div className="footer">
        <p>Anti-Hallucination Trademark Risk Assessment | Per-Mark Analysis | Validated TMEP Citations | v2.0</p>
      </div>
    </div>
  );
}

export default App;
