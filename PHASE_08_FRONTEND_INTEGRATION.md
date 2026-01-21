# Phase 8: Frontend Integration

## Overview

This phase covers integrating the backend classification results into the Next.js frontend, displaying ML-based detections in the dashboard, alerts page, and real-time monitoring views.

## Prerequisites

- Phase 7 completed (backend integration working)
- Backend running on `http://localhost:3002`
- Frontend dependencies installed
- Classification API endpoints working

## Step 1: Verify Backend Connection

### 1.1 Check Frontend Configuration

```bash
cat .env.local
```

**Required:**
```bash
NEXT_PUBLIC_FLASK_API_URL=http://localhost:3002
NEXT_PUBLIC_POLL_INTERVAL=10000
NEXT_PUBLIC_ENABLE_REAL_TIME=true
```

### 1.2 Test Backend Connection

```bash
curl http://localhost:3002/api/health
```

**Expected**: Returns health status including classifier info

## Step 2: Update Alert Types

### 2.1 Check Alert Type Definitions

```bash
grep -r "alert.*type" components/ app/
```

Frontend should handle three detection types:
- `signature`: Signature-based detection
- `anomaly`: Anomaly detection
- `classification`: ML classification (NEW)

### 2.2 Update Type Definitions

If needed, update type definitions in:
- `lib/types.ts` or similar
- Alert components
- API response types

## Step 3: Update Alert Display Components

### 3.1 Alerts Overview Component

Check `components/alerts-overview.tsx` or similar:

```typescript
// Should display classification alerts
const alertTypes = ['signature', 'anomaly', 'classification'];

// Classification alerts should show:
// - ML model prediction
// - Confidence score
// - Attack type (if available)
```

### 3.2 Alert Card Component

Update alert cards to show classification-specific info:
- Badge: "ML Classification"
- Confidence score visualization
- Model prediction details

### 3.3 Alert Filters

Add classification filter:
```typescript
<Select>
  <option value="all">All Types</option>
  <option value="signature">Signature</option>
  <option value="anomaly">Anomaly</option>
  <option value="classification">ML Classification</option>
</Select>
```

## Step 4: Update Dashboard

### 4.1 Detection Statistics

Update dashboard to show:
- Total classification detections
- Classification accuracy/confidence
- Classification vs other methods comparison

### 4.2 Real-Time Updates

Ensure WebSocket updates include classification alerts:
```typescript
socket.on('new_alert', (data) => {
  if (data.type === 'classification') {
    // Handle classification alert
  }
});
```

## Step 5: Update API Integration

### 5.1 Check API Client

Verify `lib/flask-api.ts` or similar includes:
- Alert fetching with type filter
- Classification-specific endpoints
- Model info endpoint

### 5.2 Add Classification Endpoints

If needed, add:
```typescript
// Get classification alerts
export async function getClassificationAlerts() {
  return fetch(`${API_URL}/api/alerts?type=classification`);
}

// Get model info
export async function getModelInfo() {
  return fetch(`${API_URL}/api/analyze/model-info`);
}
```

## Step 6: Add Model Information Display

### 6.1 Create Model Info Component

Create component to display:
- Model accuracy
- Training date
- Feature count
- Model type

### 6.2 Add to Dashboard

Display model info in dashboard or settings page:
```typescript
<Card>
  <CardHeader>ML Model Information</CardHeader>
  <CardContent>
    <p>Accuracy: {modelInfo.accuracy}%</p>
    <p>Model Type: {modelInfo.model_type}</p>
    <p>Features: {modelInfo.features}</p>
  </CardContent>
</Card>
```

## Step 7: Update Analysis Page

### 7.1 Show Classification Results

In analysis page, display:
- Classification prediction
- Confidence score
- Feature importance (if available)
- Comparison with other detection methods

### 7.2 Test Analysis

```bash
# Start frontend
npm run dev

# Navigate to analysis page
# Submit test packet
# Verify classification results display
```

## Step 8: Update Real-Time Dashboard

### 8.1 Real-Time Classification Alerts

Ensure real-time dashboard shows:
- Live classification detections
- Confidence scores
- Attack type predictions

### 8.2 WebSocket Integration

Verify WebSocket connection receives classification alerts:
```typescript
useEffect(() => {
  socket.on('new_alert', (alert) => {
    if (alert.type === 'classification') {
      setClassificationAlerts(prev => [alert, ...prev]);
    }
  });
}, []);
```

## Step 9: Add Confidence Visualization

### 9.1 Confidence Score Display

Show confidence scores visually:
- Progress bar
- Color coding (green/yellow/red)
- Percentage display

### 9.2 Confidence Threshold Indicator

Show when confidence exceeds threshold:
```typescript
{confidence > 0.7 && (
  <Badge variant="destructive">High Confidence</Badge>
)}
```

## Step 10: Update Statistics

### 10.1 Classification Statistics

Add to stats page:
- Total classification detections
- Average confidence
- Classification accuracy (if tracked)
- Top predicted attack types

### 10.2 Comparison Charts

Show comparison:
- Classification vs Signature detections
- Classification vs Anomaly detections
- Overlap analysis

## Step 11: Test Frontend Integration

### 11.1 Start Services

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate
python app.py
```

**Terminal 2 (Frontend):**
```bash
npm run dev
```

### 11.2 Test Scenarios

1. **View Alerts Page**
   - Navigate to `/alerts`
   - Filter by "classification"
   - Verify classification alerts display

2. **View Dashboard**
   - Navigate to `/`
   - Check classification statistics
   - Verify model info displays

3. **Real-Time Updates**
   - Navigate to `/realtime`
   - Trigger classification (if possible)
   - Verify alert appears in real-time

4. **Analysis Page**
   - Navigate to `/analysis`
   - Submit test packet
   - Verify classification results

## Step 12: Error Handling

### 12.1 Handle Missing Classification

If classification not available:
- Show message: "Classification not available"
- Fallback to other detection methods
- Don't break UI

### 12.2 Handle API Errors

```typescript
try {
  const alerts = await getClassificationAlerts();
} catch (error) {
  console.error('Failed to fetch classification alerts:', error);
  // Show user-friendly error message
}
```

## Step 13: Styling and UX

### 13.1 Visual Distinction

Make classification alerts visually distinct:
- Different icon
- Different color scheme
- "ML" badge

### 13.2 Tooltips and Help

Add tooltips explaining:
- What ML classification is
- How confidence scores work
- Difference from other detection methods

## Step 14: Troubleshooting

### Issue: Classification Alerts Not Showing

**Solutions**:
1. Check backend is running: `curl http://localhost:3002/api/health`
2. Verify API endpoint: `curl http://localhost:3002/api/alerts?type=classification`
3. Check browser console for errors
4. Verify WebSocket connection

### Issue: Frontend Not Updating

**Solutions**:
1. Check WebSocket connection status
2. Verify polling interval in `.env.local`
3. Check browser console for WebSocket errors
4. Restart frontend dev server

### Issue: Type Errors

**Solutions**:
1. Update TypeScript types to include classification
2. Check API response format matches types
3. Run `npm run build` to check for type errors

### Issue: Styling Issues

**Solutions**:
1. Check Tailwind classes are correct
2. Verify component imports
3. Check browser console for CSS errors

## Step 15: Verification Checklist

- [ ] Frontend connects to backend successfully
- [ ] Alert types include "classification"
- [ ] Classification alerts display correctly
- [ ] Alert filters work for classification
- [ ] Dashboard shows classification statistics
- [ ] Model info displays correctly
- [ ] Analysis page shows classification results
- [ ] Real-time dashboard shows classification alerts
- [ ] WebSocket updates include classifications
- [ ] Confidence scores display visually
- [ ] Statistics page includes classification data
- [ ] Error handling works correctly
- [ ] Styling is consistent
- [ ] No console errors
- [ ] All pages load without errors

## File Locations

- **Frontend Config**: `.env.local`
- **API Client**: `lib/flask-api.ts`
- **Alert Components**: `components/alerts-*.tsx`
- **Dashboard**: `app/page.tsx`
- **Analysis Page**: `app/analysis/page.tsx`
- **Real-Time**: `app/realtime/page.tsx`
- **Types**: `lib/types.ts` or similar

## Next Steps

Once frontend integration is complete and verified, proceed to:
- **Phase 9**: Testing and Optimization - End-to-end testing and performance optimization

## Estimated Time

- **Integration**: 30-45 minutes
- **Testing**: 20-30 minutes
- **Styling**: 15-20 minutes
- **Total**: 65-95 minutes

## Notes

- Frontend should gracefully handle missing classification
- Classification alerts complement other detection types
- Visual distinction helps users understand detection source
- Real-time updates provide immediate feedback
- Model info helps users understand system capabilities
