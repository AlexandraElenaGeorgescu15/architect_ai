"""
Interactive Prototype Editor with AI-Powered Real-Time Modifications

This component enables users to:
1. Chat about their prototype with AI
2. Request modifications in natural language
3. See changes applied in real-time
4. Iterate across multiple conversation turns

Author: Alexandra Georgescu
"""

import streamlit as st
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class InteractivePrototypeEditor:
    """Manages real-time prototype editing with AI assistance"""
    
    def __init__(self, agent: Any):
        """
        Initialize the editor with an AI agent.
        
        Args:
            agent: UniversalArchitectAgent instance for AI interactions
        """
        self.agent = agent
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for conversation and prototype tracking"""
        if 'prototype_conversation' not in st.session_state:
            st.session_state.prototype_conversation = []
        
        if 'current_prototype_html' not in st.session_state:
            st.session_state.current_prototype_html = None
        
        if 'prototype_version_history' not in st.session_state:
            st.session_state.prototype_version_history = []
        
        if 'prototype_file_path' not in st.session_state:
            st.session_state.prototype_file_path = None
    
    async def modify_prototype(
        self,
        current_html: str,
        modification_request: str,
        feature_context: str = ""
    ) -> str:
        """
        Modify existing prototype based on user request.
        
        Args:
            current_html: Current prototype HTML
            modification_request: User's modification request
            feature_context: Original feature context for reference
            
        Returns:
            Modified HTML
        """
        
        # Send FULL HTML for maximum context (no truncation)
        # This ensures AI sees everything and can make truly surgical changes
        
        # Build minimal, clear prompt focused on the specific change
        prompt = f"""
TASK: Modify ONE specific thing in this HTML file.

CURRENT FILE:
{current_html}

USER WANTS TO CHANGE:
{modification_request}

INSTRUCTIONS:
1. Find the exact element/line the user is talking about
2. Make ONLY that specific change
3. Keep everything else IDENTICAL
4. Output the complete modified HTML

Think step-by-step:
- What is the user asking to change?
- Where is it in the HTML?
- What's the current value?
- What should the new value be?
- Change it and output the full HTML

CRITICAL: Output the COMPLETE HTML file with the user's requested change. Do not regenerate or rewrite anything else.
"""
        
        # Call AI with simple, direct instructions
        modified_html = await self.agent._call_ai(
            prompt,
            system_prompt="You are a code editor. Make the ONE requested change and output the complete HTML. No explanations, no markdown, just HTML."
        )
        
        # Clean up if wrapped in markdown
        modified_html = self._clean_html_output(modified_html)
        
        return modified_html
    
    def _clean_html_output(self, html: str) -> str:
        """Remove markdown code fences if present"""
        html = html.strip()
        
        # Remove markdown code fences
        if html.startswith('```html'):
            html = html[7:]
        elif html.startswith('```'):
            html = html[3:]
        
        if html.endswith('```'):
            html = html[:-3]
        
        return html.strip()
    
    def save_version(self, html: str, message: str = ""):
        """Save current version to history"""
        version = {
            'timestamp': datetime.now().isoformat(),
            'html': html,
            'message': message,
            'version_number': len(st.session_state.prototype_version_history) + 1
        }
        st.session_state.prototype_version_history.append(version)
    
    def restore_version(self, version_number: int) -> Optional[str]:
        """Restore a previous version"""
        versions = st.session_state.prototype_version_history
        for version in versions:
            if version['version_number'] == version_number:
                return version['html']
        return None
    
    def save_to_file(self, html: str, filename: str = None, mode: str = "pm") -> Path:
        """Save prototype to outputs directory - always to the same file per mode"""
        # Use ABSOLUTE path based on this file's location (same as AppConfig)
        _MODULE_ROOT = Path(__file__).parent.parent  # architect_ai_cursor_poc/
        outputs_dir = _MODULE_ROOT / "outputs" / "prototypes"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Always save to the mode-specific file (not timestamped files)
        if filename is None:
            if mode == "pm":
                filename = "pm_visual_prototype.html"
            else:  # dev mode
                filename = "developer_visual_prototype.html"
        
        file_path = outputs_dir / filename
        file_path.write_text(html, encoding='utf-8')
        
        # ULTRA-NUCLEAR CACHE BUSTING
        import random
        current_time = datetime.now().isoformat()
        random_salt = str(random.randint(1000000, 9999999))
        file_mtime = file_path.stat().st_mtime
        file_size = file_path.stat().st_size
        
        # Store EVERYTHING for cache busting
        st.session_state.prototype_file_path = str(file_path)
        st.session_state.prototype_last_modified = current_time
        st.session_state[f'prototype_cache_buster_{mode}'] = f"{file_mtime}_{file_size}_{random_salt}"
        st.session_state[f'force_reload_{mode}'] = True
        
        # Force refresh flag for outputs tab
        if mode == "pm":
            st.session_state.pm_prototype_updated = True
            st.session_state.pm_prototype_last_save = current_time
            st.session_state.pm_prototype_force_mtime = file_mtime
            # CRITICAL: Clear any cached HTML
            if 'pm_cached_html' in st.session_state:
                del st.session_state['pm_cached_html']
        else:
            st.session_state.dev_prototype_updated = True
            st.session_state.dev_prototype_last_save = current_time
            st.session_state.dev_prototype_force_mtime = file_mtime
            # CRITICAL: Clear any cached HTML
            if 'dev_cached_html' in st.session_state:
                del st.session_state['dev_cached_html']
        
        # NUCLEAR OPTION: Force immediate rerun to update outputs tab
        st.rerun()
        
        return file_path
    
    def load_from_file(self, file_path: str) -> str:
        """Load prototype from file"""
        return Path(file_path).read_text(encoding='utf-8')


def render_interactive_prototype_editor(agent: Any, initial_html: str = None, feature_context: str = "", mode: str = "pm"):
    """
    Render the interactive prototype editor UI component.
    
    Args:
        agent: UniversalArchitectAgent instance
        initial_html: Initial prototype HTML (if any)
        feature_context: Original feature context for AI reference
        mode: "pm" or "dev" - determines save file name
    """
    
    editor = InteractivePrototypeEditor(agent)
    
    # Initialize with provided HTML if available
    if initial_html and st.session_state.current_prototype_html is None:
        st.session_state.current_prototype_html = initial_html
        editor.save_version(initial_html, "Initial prototype")
    
    st.markdown("### 🎨 Interactive Prototype Editor")
    st.markdown("Chat with AI to modify your prototype in real-time. Make it perfect!")
    
    # Two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 💬 AI Chat")
        
        # Display conversation history
        if st.session_state.prototype_conversation:
            with st.container():
                for message in st.session_state.prototype_conversation:
                    role = message['role']
                    content = message['content']
                    
                    if role == 'user':
                        st.markdown(f"**You:** {content}")
                    else:
                        st.markdown(f"**AI:** {content}")
                    
                    st.markdown("---")
        
        # Chat input
        with st.form("chat_form", clear_on_submit=True):
            user_message = st.text_area(
                "What would you like to change?",
                placeholder="e.g., 'Add a search bar at the top', 'Change the color scheme to blue', 'Add a confirmation dialog when deleting'",
                height=100,
                key="prototype_chat_input"
            )
            
            col_a, col_b = st.columns([3, 1])
            with col_a:
                submit_chat = st.form_submit_button("💬 Send", use_container_width=True)
            with col_b:
                clear_chat = st.form_submit_button("🗑️ Clear", use_container_width=True)
        
        # Handle clear
        if clear_chat:
            st.session_state.prototype_conversation = []
            st.rerun()
        
        # Handle chat submission
        if submit_chat and user_message.strip():
            if st.session_state.current_prototype_html is None:
                st.error("⚠️ No prototype loaded. Please generate a prototype first.")
            else:
                with st.spinner("🤖 AI is modifying your prototype..."):
                    # Add user message to conversation
                    st.session_state.prototype_conversation.append({
                        'role': 'user',
                        'content': user_message,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Modify prototype
                    try:
                        modified_html = asyncio.run(
                            editor.modify_prototype(
                                st.session_state.current_prototype_html,
                                user_message,
                                feature_context
                            )
                        )
                        
                        # DETAILED CHANGE ANALYSIS
                        old_html = st.session_state.current_prototype_html
                        old_length = len(old_html)
                        new_length = len(modified_html)
                        length_diff = new_length - old_length
                        
                        # Check if ANYTHING changed
                        if old_html == modified_html:
                            st.error(f"🚫 **NO CHANGES DETECTED!** AI returned identical HTML. Request: '{user_message}'")
                            st.warning("The AI did not make any changes. Try being more specific or regenerate.")
                            # Don't save if nothing changed
                            st.session_state.prototype_conversation.append({
                                'role': 'assistant',
                                'content': f"❌ No changes made for: '{user_message}'. Try being more specific.",
                                'timestamp': datetime.now().isoformat()
                            })
                            st.rerun()
                            return  # Exit early
                        
                        # Show similarity
                        if old_length > 0:
                            similarity = (1 - abs(length_diff) / old_length) * 100
                            
                            if similarity < 50:
                                st.error(f"❌ AI REWROTE EVERYTHING! Similarity: {similarity:.1f}%")
                                st.warning("This is NOT a surgical change. The entire HTML was regenerated.")
                            elif similarity < 98:
                                st.warning(f"⚠️ Large change: Similarity: {similarity:.1f}% (Target: >98%)")
                            else:
                                st.success(f"✅ Surgical change: Similarity: {similarity:.1f}%")
                        
                        # Show what specifically changed (first difference)
                        import difflib
                        diff = list(difflib.unified_diff(
                            old_html.splitlines(keepends=True)[:50],  # First 50 lines
                            modified_html.splitlines(keepends=True)[:50],
                            lineterm='',
                            n=1
                        ))
                        
                        if diff:
                            with st.expander("🔍 Show Changes (first 50 lines)", expanded=False):
                                diff_text = ''.join(diff[:30])  # First 30 diff lines
                                st.code(diff_text, language='diff')
                        
                        # Update prototype
                        st.session_state.current_prototype_html = modified_html
                        
                        # Save version
                        editor.save_version(modified_html, user_message[:50])
                        
                        # Auto-save to the main file - WITH COMPREHENSIVE VERIFICATION
                        auto_saved = False
                        save_error = None
                        file_size = 0
                        
                        try:
                            # Save
                            saved_path = editor.save_to_file(modified_html, mode=mode)
                            st.success(f"✅ File written to: `{saved_path}`")
                            
                            # VERIFY: Read back the file to confirm
                            from pathlib import Path
                            if not Path(saved_path).exists():
                                st.error(f"❌ FILE DOESN'T EXIST after save: {saved_path}")
                                auto_saved = False
                            else:
                                # Read it back
                                saved_content = Path(saved_path).read_text(encoding='utf-8')
                                file_size = len(saved_content)
                                
                                # Verify content matches
                                if saved_content == modified_html:
                                    st.success(f"✅ VERIFIED: File content matches ({file_size} bytes)")
                                    auto_saved = True
                                else:
                                    st.error("❌ FILE CONTENT MISMATCH! What was saved doesn't match what was generated.")
                                    st.warning(f"Expected: {len(modified_html)} bytes, Got: {file_size} bytes")
                                    auto_saved = False
                                
                                # Check if it contains the user's requested change
                                search_terms = user_message.lower().split()
                                found_terms = [term for term in search_terms if term in saved_content.lower()]
                                st.info(f"🔍 Searching file for your keywords: {len(found_terms)}/{len(search_terms)} found")
                                
                        except Exception as e:
                            save_error = str(e)
                            st.error(f"❌ Save EXCEPTION: {save_error}")
                            import traceback
                            st.code(traceback.format_exc())
                        
                        # Add AI response to conversation
                        response_msg = "✅ Prototype updated! Check the preview on the right."
                        if auto_saved:
                            response_msg += f"\n\n💡 **Auto-saved to file!** Size: {file_size} bytes"
                        else:
                            response_msg += f"\n\n⚠️ **Save failed:** {save_error or 'Unknown error'}"
                        
                        st.session_state.prototype_conversation.append({
                            'role': 'assistant',
                            'content': response_msg,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        if auto_saved:
                            st.success(f"✅ Prototype modified & saved! ({file_size} bytes)")
                            st.info("💡 **Next step:** Go to the **📊 Outputs** tab and click **🔄 Force Refresh** to see your changes!")
                        else:
                            st.warning("⚠️ Prototype modified but NOT saved to file")
                        
                        # Offer to download the current version for verification
                        st.download_button(
                            label="⬇️ Download Current Version (for verification)",
                            data=modified_html,
                            file_name=f"{mode}_prototype_modified_{datetime.now().strftime('%H%M%S')}.html",
                            mime="text/html",
                            key=f"download_after_mod_{datetime.now().timestamp()}"
                        )
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error modifying prototype: {str(e)}")
                        st.session_state.prototype_conversation.append({
                            'role': 'assistant',
                            'content': f"❌ Sorry, I encountered an error: {str(e)}",
                            'timestamp': datetime.now().isoformat()
                        })
    
    with col2:
        st.markdown("#### 👁️ Live Preview")
        
        if st.session_state.current_prototype_html:
            # Version history
            if len(st.session_state.prototype_version_history) > 1:
                with st.expander("📜 Version History"):
                    for version in reversed(st.session_state.prototype_version_history):
                        col_v1, col_v2, col_v3 = st.columns([2, 1, 1])
                        with col_v1:
                            st.markdown(f"**Version {version['version_number']}**: {version['message'][:50]}")
                            st.caption(version['timestamp'])
                        with col_v2:
                            if st.button("👁️", key=f"view_v{version['version_number']}", use_container_width=True, help="View this version (preview only)"):
                                restored = editor.restore_version(version['version_number'])
                                if restored:
                                    st.session_state.current_prototype_html = restored
                                    st.info(f"📖 Viewing version {version['version_number']}. Click '💾 Save to File' below to make it current in Outputs.")
                                    st.rerun()
                        with col_v3:
                            if st.button("💾", key=f"save_v{version['version_number']}", use_container_width=True, help="Restore & Save to Outputs"):
                                restored = editor.restore_version(version['version_number'])
                                if restored:
                                    try:
                                        # Update current HTML
                                        st.session_state.current_prototype_html = restored
                                        # Save to file immediately
                                        file_path = editor.save_to_file(restored, mode=mode)
                                        st.success(f"✅ Version {version['version_number']} restored & saved to Outputs!")
                                        st.balloons()
                                        # save_to_file will trigger st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error saving: {e}")
            
            # Action buttons
            col_action1, col_action2, col_action3 = st.columns(3)
            
            with col_action1:
                if st.button("💾 Save to File", use_container_width=True):
                    try:
                        file_path = editor.save_to_file(st.session_state.current_prototype_html, mode=mode)
                        
                        # CRITICAL: The save_to_file method updates session state, but we need to verify
                        from pathlib import Path
                        if Path(file_path).exists():
                            file_size = Path(file_path).stat().st_size
                            st.success(f"✅ Saved successfully! ({file_size} bytes)")
                            st.info("💡 Go to the **📊 Outputs** tab and click **🔄 Force Refresh** to see your changes")
                            
                            # Show what was saved
                            with st.expander("🔍 Verify Saved Content"):
                                saved_html = Path(file_path).read_text(encoding='utf-8')
                                st.code(saved_html[:500] + "..." if len(saved_html) > 500 else saved_html, language='html')
                        else:
                            st.error("❌ File doesn't exist after save!")
                    except Exception as e:
                        st.error(f"❌ Error saving: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            
            with col_action2:
                if st.button("📋 Copy HTML", use_container_width=True):
                    st.code(st.session_state.current_prototype_html, language='html')
            
            with col_action3:
                # Download button
                st.download_button(
                    label="⬇️ Download",
                    data=st.session_state.current_prototype_html,
                    file_name=f"prototype_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True
                )
            
            # Preview
            st.markdown("---")
            st.components.v1.html(
                st.session_state.current_prototype_html,
                height=600,
                scrolling=True
            )
            
        else:
            st.info("👈 Generate a prototype first, then come back here to modify it!")


def render_quick_modification_buttons(agent: Any, feature_context: str = "", mode: str = "pm"):
    """
    Render quick modification buttons for common changes.
    
    Args:
        agent: UniversalArchitectAgent instance
        feature_context: Original feature context
        mode: "pm" or "dev" - determines save file name
    """
    
    st.markdown("#### ⚡ Quick Modifications")
    
    col1, col2, col3, col4 = st.columns(4)
    
    editor = InteractivePrototypeEditor(agent)
    
    modifications = [
        ("🎨 Make it darker", "Change the color scheme to a dark theme with dark backgrounds and light text"),
        ("🔍 Add search", "Add a search bar at the top that allows filtering/searching the content"),
        ("📱 Mobile optimize", "Optimize the layout for mobile devices with better responsive design"),
        ("✨ Add animations", "Add smooth animations and transitions to make interactions feel more polished"),
    ]
    
    for i, (label, request) in enumerate(modifications):
        with [col1, col2, col3, col4][i]:
            if st.button(label, use_container_width=True, key=f"quick_mod_{i}"):
                if st.session_state.current_prototype_html:
                    with st.spinner(f"Applying: {label}..."):
                        try:
                            modified = asyncio.run(
                                editor.modify_prototype(
                                    st.session_state.current_prototype_html,
                                    request,
                                    feature_context
                                )
                            )
                            st.session_state.current_prototype_html = modified
                            editor.save_version(modified, label)
                            # Auto-save to main file - DON'T FAIL SILENTLY
                            auto_saved = False
                            try:
                                saved_path = editor.save_to_file(modified, mode=mode)
                                auto_saved = True
                                from pathlib import Path
                                file_size = Path(saved_path).stat().st_size if Path(saved_path).exists() else 0
                            except Exception as e:
                                st.error(f"❌ Save failed: {str(e)}")
                            
                            success_msg = f"✅ {label} applied!"
                            if auto_saved:
                                success_msg += f" (Saved: {file_size} bytes)"
                            else:
                                success_msg += " (⚠️ NOT saved to file)"
                            st.success(success_msg)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ No prototype loaded")

