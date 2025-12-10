"""
Version History UI Component

Provides Streamlit UI for viewing, restoring, and comparing artifact versions.
Integrates with the VersionManager to display version history and enable
version management operations.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import VersionManager
import sys
sys.path.append(str(Path(__file__).parent.parent))
from versioning.version_manager import VersionManager, Version


def render_version_history():
    """
    Render version history panel in Streamlit.
    
    Displays:
    - Version list for each artifact type
    - Version details (timestamp, score, attempts)
    - Restore and compare actions
    - Tags and notes management
    - Statistics dashboard
    """
    st.markdown("### 📚 Version History")
    
    st.markdown("""
    View, restore, and compare previous versions of generated artifacts.
    Versions are automatically saved each time you generate an artifact.
    """)
    
    # Initialize version manager
    vm = VersionManager()
    
    # Get statistics
    stats = vm.get_statistics()
    
    if stats.get('total_versions', 0) == 0:
        st.info("📭 No version history yet. Generate some artifacts to build version history!")
        return
    
    # Display statistics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Versions", stats['total_versions'])
    
    with col2:
        st.metric("Artifact Types", stats['total_artifacts'])
    
    with col3:
        storage_mb = stats['total_size'] / (1024 * 1024)
        st.metric("Storage Used", f"{storage_mb:.2f} MB")
    
    with col4:
        avg_score = stats.get('avg_validation_score', 0.0)
        score_color = "🟢" if avg_score >= 80 else "🟡" if avg_score >= 60 else "🔴"
        st.metric("Avg Quality", f"{score_color} {avg_score:.1f}")
    
    st.markdown("---")
    
    # Artifact selector
    artifact_types = list(stats['by_artifact'].keys())
    
    if not artifact_types:
        st.warning("No artifacts with version history")
        return
    
    selected_artifact = st.selectbox(
        "Select Artifact Type:",
        options=artifact_types,
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    # Get versions for selected artifact
    versions = vm.get_versions(selected_artifact)
    
    if not versions:
        st.warning(f"No versions found for {selected_artifact}")
        return
    
    st.success(f"Found {len(versions)} version(s)")
    
    # Display mode
    display_mode = st.radio(
        "Display Mode:",
        options=["📋 List View", "📊 Changelog", "🔍 Compare Versions"],
        horizontal=True
    )
    
    if display_mode == "📋 List View":
        render_list_view(vm, selected_artifact, versions)
    
    elif display_mode == "📊 Changelog":
        render_changelog_view(vm, selected_artifact)
    
    elif display_mode == "🔍 Compare Versions":
        render_compare_view(vm, selected_artifact, versions)


def render_list_view(vm: VersionManager, artifact_type: str, versions: list):
    """Render list view of versions"""
    st.markdown("---")
    
    for i, version in enumerate(versions):
        with st.expander(
            f"Version {len(versions) - i} - {datetime.fromisoformat(version.timestamp).strftime('%Y-%m-%d %H:%M:%S')}",
            expanded=(i == 0)
        ):
            # Version details
            col1, col2, col3 = st.columns(3)
            
            with col1:
                score_color = "🟢" if version.validation_score >= 80 else "🟡" if version.validation_score >= 60 else "🔴"
                st.metric("Quality Score", f"{score_color} {version.validation_score:.1f}/100")
            
            with col2:
                st.metric("Generation Attempts", version.attempt_count)
            
            with col3:
                size_kb = version.file_size / 1024
                st.metric("Size", f"{size_kb:.1f} KB")
            
            # Tags
            if version.tags:
                st.markdown(f"**Tags:** {', '.join([f'`{tag}`' for tag in version.tags])}")
            
            # Notes
            if version.notes:
                st.markdown(f"**Notes:** {version.notes}")
            
            # Content preview
            st.markdown("**Content Preview:**")
            preview_length = 500
            preview = version.content[:preview_length]
            if len(version.content) > preview_length:
                preview += "\n\n... (truncated)"
            
            st.code(preview, language='markdown')
            
            # Actions
            st.markdown("---")
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button(f"📥 Restore", key=f"restore_{version.version_id}"):
                    restore_version(vm, artifact_type, version)
            
            with action_col2:
                if st.button(f"📝 View Full", key=f"view_{version.version_id}"):
                    view_full_version(vm, artifact_type, version)
            
            with action_col3:
                if st.button(f"🏷️ Add Tag", key=f"tag_{version.version_id}"):
                    add_tag_dialog(vm, artifact_type, version)
            
            with action_col4:
                if st.button(f"🗑️ Delete", key=f"delete_{version.version_id}"):
                    delete_version(vm, artifact_type, version)


def render_changelog_view(vm: VersionManager, artifact_type: str):
    """Render changelog view"""
    st.markdown("---")
    
    changelog = vm.get_changelog(artifact_type, limit=10)
    st.markdown(changelog)
    
    # Download changelog
    st.download_button(
        label="📥 Download Changelog",
        data=changelog,
        file_name=f"{artifact_type}_changelog.md",
        mime="text/markdown"
    )


def render_compare_view(vm: VersionManager, artifact_type: str, versions: list):
    """Render comparison view"""
    st.markdown("---")
    
    if len(versions) < 2:
        st.warning("Need at least 2 versions to compare")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        version1_idx = st.selectbox(
            "Select First Version:",
            options=range(len(versions)),
            format_func=lambda i: f"Version {len(versions) - i} ({datetime.fromisoformat(versions[i].timestamp).strftime('%Y-%m-%d %H:%M')})",
            key=f"compare_v1_{artifact_type}"
        )
    
    with col2:
        version2_idx = st.selectbox(
            "Select Second Version:",
            options=range(len(versions)),
            index=min(1, len(versions) - 1),
            format_func=lambda i: f"Version {len(versions) - i} ({datetime.fromisoformat(versions[i].timestamp).strftime('%Y-%m-%d %H:%M')})",
            key=f"compare_v2_{artifact_type}"
        )
    
    if version1_idx == version2_idx:
        st.warning("Please select two different versions to compare")
        return
    
    version1 = versions[version1_idx]
    version2 = versions[version2_idx]
    
    # Display format selector (OUTSIDE the comparison results to avoid rerun)
    diff_mode = st.radio(
        "Display Format:", 
        ["Unified Diff", "Side-by-Side"], 
        horizontal=True,
        key=f"diff_mode_{artifact_type}"
    )
    
    # Initialize session state for comparison results
    comparison_key = f"comparison_{artifact_type}_{version1.version_id}_{version2.version_id}"
    
    if st.button("🔍 Compare Versions", type="primary", key=f"compare_btn_{artifact_type}"):
        comparison = vm.compare_versions(
            artifact_type,
            version1.version_id,
            version2.version_id
        )
        # Store in session state so it persists across reruns
        st.session_state[comparison_key] = comparison
    
    # Display comparison if it exists in session state
    if comparison_key in st.session_state:
        comparison = st.session_state[comparison_key]
        
        if comparison:
            st.success("Comparison complete!")
            
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Changes", comparison['changes'])
            with col2:
                st.metric("Additions", f"+{comparison['additions']}")
            with col3:
                st.metric("Deletions", f"-{comparison['deletions']}")
            
            st.markdown("---")
            
            if diff_mode == "Unified Diff":
                st.code(comparison['diff'], language='diff')
            else:
                # Better styled HTML diff
                st.markdown("#### Side-by-Side Comparison")
                
                # Create better diff display using columns
                lines1 = comparison['version1'].content.splitlines()
                lines2 = comparison['version2'].content.splitlines()
                
                max_lines = max(len(lines1), len(lines2))
                
                # Simple table-based side-by-side comparison
                diff_html = """
                <style>
                .diff-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    background: white;
                }
                .diff-table th {
                    background: #f0f0f0;
                    padding: 8px;
                    text-align: center;
                    border: 1px solid #ddd;
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                }
                .diff-table td {
                    border: 1px solid #e0e0e0;
                    padding: 4px 8px;
                    vertical-align: top;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
                .diff-linenum {
                    width: 40px;
                    background: #f8f9fa;
                    color: #666;
                    text-align: right;
                    user-select: none;
                }
                .diff-old {
                    background: #ffebe9;
                }
                .diff-new {
                    background: #e6ffec;
                }
                .diff-wrapper {
                    max-height: 600px;
                    overflow: auto;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                </style>
                <div class="diff-wrapper">
                <table class="diff-table">
                    <thead>
                        <tr>
                            <th colspan="2">Version """ + str(len(versions) - version1_idx) + """ (""" + comparison['version1'].timestamp[:10] + """)</th>
                            <th colspan="2">Version """ + str(len(versions) - version2_idx) + """ (""" + comparison['version2'].timestamp[:10] + """)</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                # Show first 100 lines to avoid performance issues
                display_lines = min(100, max_lines)
                
                for i in range(display_lines):
                    line1 = lines1[i] if i < len(lines1) else ""
                    line2 = lines2[i] if i < len(lines2) else ""
                    
                    # Escape HTML
                    line1_escaped = line1.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') if line1 else '&nbsp;'
                    line2_escaped = line2.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') if line2 else '&nbsp;'
                    
                    # Determine styling
                    is_different = line1 != line2
                    old_class = 'diff-old' if is_different and line1 else ''
                    new_class = 'diff-new' if is_different and line2 else ''
                    
                    diff_html += f"""
                        <tr>
                            <td class="diff-linenum">{i+1 if line1 else ''}</td>
                            <td class="{old_class}">{line1_escaped}</td>
                            <td class="diff-linenum">{i+1 if line2 else ''}</td>
                            <td class="{new_class}">{line2_escaped}</td>
                        </tr>
                    """
                
                diff_html += """
                    </tbody>
                </table>
                </div>
                """
                
                if max_lines > 100:
                    diff_html += f"<p style='text-align: center; padding: 10px; background: #fff3cd; margin-top: 10px;'>⚠️ Showing first 100 of {max_lines} lines</p>"
                
                st.components.v1.html(diff_html, height=650, scrolling=True)
            
            # Download diff
            st.download_button(
                label="📥 Download Diff",
                data=comparison['diff'],
                file_name=f"{artifact_type}_diff_{version1.version_id}_vs_{version2.version_id}.diff",
                mime="text/plain",
                key=f"download_diff_{artifact_type}"
            )


def restore_version(vm: VersionManager, artifact_type: str, version: Version):
    """Restore a version to current outputs"""
    from app_v2 import AppConfig
    
    # Determine output path based on artifact type
    output_paths = {
        'erd': AppConfig.OUTPUTS_DIR / "visualizations" / "erd_diagram.mmd",
        'architecture': AppConfig.OUTPUTS_DIR / "visualizations" / "architecture_diagram.mmd",
        'api_docs': AppConfig.OUTPUTS_DIR / "documentation" / "api.md",
        'jira': AppConfig.OUTPUTS_DIR / "documentation" / "jira_tasks.md",
        'workflows': AppConfig.OUTPUTS_DIR / "workflows" / "workflows.md",
        'visual_prototype_dev': AppConfig.OUTPUTS_DIR / "prototypes" / "developer_visual_prototype.html",
    }
    
    output_path = output_paths.get(artifact_type)
    
    if not output_path:
        st.error(f"Unknown artifact type: {artifact_type}")
        return
    
    if vm.restore_version(artifact_type, version.version_id, output_path):
        st.success(f"✅ Restored version to: {output_path.name}")
        st.balloons()
    else:
        st.error("❌ Failed to restore version")


def view_full_version(vm: VersionManager, artifact_type: str, version: Version):
    """Display full version content in a modal"""
    st.markdown("---")
    st.markdown(f"### Full Content: Version {version.version_id}")
    
    # Load full content
    full_version = vm.get_version(artifact_type, version.version_id)
    if full_version:
        st.code(full_version.content, language='markdown')
        
        # Download button
        st.download_button(
            label="📥 Download",
            data=full_version.content,
            file_name=f"{artifact_type}_{version.version_id}.txt",
            mime="text/plain"
        )
    else:
        st.error("Failed to load full content")


def add_tag_dialog(vm: VersionManager, artifact_type: str, version: Version):
    """Show dialog to add tag"""
    tag = st.text_input(f"Enter tag for version {version.version_id}:", key=f"tag_input_{version.version_id}")
    
    if tag:
        if vm.add_tag(artifact_type, version.version_id, tag):
            st.success(f"✅ Added tag: {tag}")
            st.rerun()
        else:
            st.error("Failed to add tag")


def delete_version(vm: VersionManager, artifact_type: str, version: Version):
    """Delete a version with confirmation"""
    if st.checkbox(f"Confirm deletion of version {version.version_id}", key=f"confirm_delete_{version.version_id}"):
        if vm.delete_version(artifact_type, version.version_id):
            st.success("✅ Version deleted")
            st.rerun()
        else:
            st.error("Failed to delete version")

