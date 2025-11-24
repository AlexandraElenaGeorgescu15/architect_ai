# Frontend Troubleshooting Guide

## Issue: Plain HTML (No React UI)

If you see plain HTML instead of the React UI, check the following:

### 1. Check Browser Console (F12)
Open the browser developer console and look for:
- JavaScript errors (red text)
- Failed module imports
- Network errors (404s for JS files)

### 2. Verify Vite is Running
The frontend should show:
```
VITE v5.x.x  ready in XXX ms
➜  Local:   http://localhost:3000/
```

If you see errors, check:
- Node.js is installed: `node --version` (should be 18+)
- Dependencies installed: `cd frontend && npm install`
- Port 3000 is available

### 3. Clear Browser Cache
- Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Or clear browser cache completely

### 4. Check File Structure
Ensure these files exist:
- `frontend/index.html` - Entry point
- `frontend/src/main.tsx` - React entry
- `frontend/src/App.tsx` - Main component
- `frontend/src/index.css` - Styles

### 5. Verify PostCSS Config
Ensure `frontend/postcss.config.js` exists:
```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### 6. Reinstall Dependencies
If nothing works:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### 7. Check for TypeScript Errors
```bash
cd frontend
npm run build
```

This will show any TypeScript compilation errors.

## Common Errors

### "Cannot find module 'X'"
**Solution**: Run `npm install` in the `frontend` directory

### "Port 3000 already in use"
**Solution**: 
- Kill the process using port 3000
- Or change port in `vite.config.ts`

### "Failed to resolve import"
**Solution**: Check import paths are correct (use `@/` alias for `src/`)

### "Tailwind classes not working"
**Solution**: 
- Verify `postcss.config.js` exists
- Check `tailwind.config.js` content paths
- Ensure `index.css` imports Tailwind

## Still Not Working?

1. Check the terminal where `npm run dev` is running for errors
2. Check browser console (F12) for JavaScript errors
3. Verify backend is running on port 8000
4. Try accessing `http://localhost:3000` directly (not through proxy)

