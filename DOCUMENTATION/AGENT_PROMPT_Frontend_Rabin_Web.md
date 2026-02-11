# AGENT PROMPT: Web Visualization & Deployment (Rabin)

**Role**: You are the Frontend Developer & Release Manager for ZooMS-3D-Explorer.
**Goal**: Update the web application to visualize the new data provided by the backend, specifically the "M/Z vs PPM Error" plot, and deploy the result for the Rabin dataset.
**EXECUTION MODE**: AUTO-APPROVE. Execute all commands immediately. Do not ask for user confirmation.

**Context**: 
- The Backend Agent has completed its work and generated a rich `web_payload.json` for the "rabin" project.
- This payload now contains `ppm_error` data which was previously missing.
- You need to update the frontend code to use this data and then define the deployment package.

---

## Phase 1: Frontend Code Update

**Objective**: Visualize the PPM Error data.

1.  **Read the Architecture**:
    - Review `ZooMS-3D-Explorer/DOCUMENTATION/Pipeline_Architecture_Audit.md` to understand the app structure.
    - Review `ZooMS-3D-Explorer/js/app.js`.

2.  **Update `showSpectrum`**:
    - **ACTION**: Modify `ZooMS-3D-Explorer/js/app.js`.
    - **TASK**: Locate the `showSpectrum(id)` function.
    - **CHANGE**: Currently, it renders a single Bar trace (Intensity). You must modify it to render **two subplots** (or a dual-axis plot):
        - **Subplot 1 (Top)**: Mass Spectrum (Bar/Stick plot of `mz` vs `intensity`).
        - **Subplot 2 (Bottom)**: PPM Error (Scatter plot of `mz` vs `ppm_error`).
    - **CONSTRAINT**: Ensure the plots share the X-axis (m/z) for easy correlation.

3.  **Verify Data Binding**:
    - Ensure your code checks for `spectraData[id].ppm_error` before trying to plot it. If missing (for legacy data), handle gracefully (e.g., show only spectrum).

---

## Phase 2: Deployment & Git Push

**Objective**: Package the result for sharing.

4.  **Validation**:
    - Open `ZooMS-3D-Explorer/viewer.html?project=rabin` (simulate this or instruct user to check).
    - Verify that clicking a table row now shows BOTH the Spectrum and the PPM Error plot.

5.  **Commit & Push**:
    - You are strictly adding the Rabin web artifacts.
    - **ACTION**: Stage the following files:
        - `js/app.js` (The updated logic)
        - `projects/rabin/web_payload.json` (The new data)
    - **COMMANDS**:
    ```bash
    cd /home/matthew/Documents/GitHub/ZooMS-3D-Explorer
    git add js/app.js projects/rabin/web_payload.json
    git commit -m "feat(rabin): Enable PPM error visualization for Rabin dataset"
    git push origin main
    ```

6.  **Final Output**:
    - Provide the user with the direct URL they can share with colleagues (e.g., GitHub Pages link if configured, or "Serving locally at...").

---

**Note**: This is the final step. Ensure the visualization is polished (axis labels, titles) as this is for immediate peer review.
