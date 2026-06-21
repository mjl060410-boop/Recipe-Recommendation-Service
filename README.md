# Recipe-Recommendation-Service

                        if st.button("❌ 영구 삭제", key=f"purge_single_{t_idx}", use_container_width=True):
                            new_trash = [t for t in trash_data if t.get("timestamp") != entry.get("timestamp")]
                            save_trash(new_trash)
                            st.toast("기록이 영구 삭제되었습니다.", icon="❌")
                            st.rerun()
