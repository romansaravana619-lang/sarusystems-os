import { useEffect, useState } from "react";
import { createSocialPost, getSocialDashboard, getSocialPosts, updateSocialPerformance, updateSocialPost, type SocialDashboard, type SocialPost } from "./socialMediaApi";

const emptyMetrics = { impressions: 0, reach: 0, likes: 0, comments: 0, shares: 0, saves: 0, clicks: 0, views: 0 };

export default function SocialMediaPage({ token }: { token: string }) {
  const [d, setD] = useState<SocialDashboard | null>(null);
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [platform, setPlatform] = useState("linkedin");
  const [postId, setPostId] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [contentAssetId, setContentAssetId] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const [creativeUrl, setCreativeUrl] = useState("");
  const [externalLink, setExternalLink] = useState("");
  const [altText, setAltText] = useState("");
  const [notes, setNotes] = useState("");
  const [schedule, setSchedule] = useState("");
  const [metricPost, setMetricPost] = useState<SocialPost | null>(null);
  const [metrics, setMetrics] = useState(emptyMetrics);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    const [dashboard, list] = await Promise.all([getSocialDashboard(token), getSocialPosts(token)]);
    setD(dashboard);
    setPosts(list);
  };
  useEffect(() => { void load().catch((e: unknown) => setError(e instanceof Error ? e.message : "Unable to load social media records.")); }, [token]);

  const create = async () => {
    if (!postId.trim()) { setError("Enter the platform post/video/page ID used to identify this record."); return; }
    setBusy(true); setError("");
    try {
      await createSocialPost(token, {
        platform, post_id: postId.trim(), post_title: title || null, post_content: content || null,
        content_asset_id: contentAssetId.trim() || null, campaign_id: campaignId.trim() || null,
        creative_url: creativeUrl || null, external_link: externalLink || null, alt_text: altText || null,
        notes: notes || null, status: "draft",
      });
      setPostId(""); setTitle(""); setContent(""); setContentAssetId(""); setCampaignId("");
      setCreativeUrl(""); setExternalLink(""); setAltText(""); setNotes(""); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to create post."); }
    finally { setBusy(false); }
  };

  const move = async (post: SocialPost, status: string) => {
    setError("");
    try {
      const postDate = status === "scheduled" ? (schedule ? new Date(schedule).toISOString() : post.post_date) : post.post_date;
      if (status === "scheduled" && (!postDate || new Date(postDate).getTime() <= Date.now())) { setError("Choose a future publishing date and time before scheduling."); return; }
      await updateSocialPost(token, post.id, { status, post_date: postDate }); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to update publishing status."); }
  };

  const openMetrics = (post: SocialPost) => { setMetricPost(post); setMetrics({ impressions: post.impressions, reach: post.reach, likes: post.likes, comments: post.comments, shares: post.shares, saves: post.saves, clicks: post.clicks, views: post.views }); };
  const saveMetrics = async () => {
    if (!metricPost) return;
    setBusy(true); setError("");
    try { await updateSocialPerformance(token, metricPost.id, metrics); setMetricPost(null); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to save performance metrics."); }
    finally { setBusy(false); }
  };

  return <section className="module-panel">
    <div className="section-header"><div><p className="eyebrow">4.13 SOCIAL MEDIA</p><h2>Social Media Command Workspace</h2><p>Instagram · Facebook · LinkedIn · YouTube · Website · publishing schedule · performance.</p><p>Publishing status is tracked here. This workspace does not call platform APIs or auto-publish without a configured provider integration.</p></div></div>
    {error && <p role="alert" className="error-message">{error}</p>}
    {d && <><div className="metric-grid"><article><strong>{d.total_posts}</strong><span>Total Posts</span></article><article><strong>{d.drafts}</strong><span>Drafts</span></article><article><strong>{d.ready}</strong><span>Ready</span></article><article><strong>{d.scheduled}</strong><span>Scheduled</span></article><article><strong>{d.published}</strong><span>Published</span></article></div>
    <div className="metric-grid"><article><strong>{d.performance.reach || 0}</strong><span>Total Reach</span></article><article><strong>{d.performance.impressions || 0}</strong><span>Impressions</span></article><article><strong>{d.performance.likes || 0}</strong><span>Likes</span></article><article><strong>{d.performance.comments || 0}</strong><span>Comments</span></article><article><strong>{d.performance.views || 0}</strong><span>Views</span></article></div></>}
    <div className="module-grid"><section className="module-card"><h3>Create Platform Post</h3><div className="form-grid">
      <label>Platform<select value={platform} onChange={e => setPlatform(e.target.value)}><option value="linkedin">LinkedIn</option><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="youtube">YouTube</option><option value="website">Website</option></select></label>
      <label>Post / video / page ID<input value={postId} onChange={e => setPostId(e.target.value)} placeholder="Unique platform reference" required /></label>
      <label>Post title<input value={title} onChange={e => setTitle(e.target.value)} placeholder="Post title" /></label>
      <label>Post content / caption<textarea value={content} onChange={e => setContent(e.target.value)} placeholder="Platform-specific content" /></label>
      <label>Content Asset UUID<input value={contentAssetId} onChange={e => setContentAssetId(e.target.value)} placeholder="Link to existing content_assets record" /></label>
      <label>Campaign UUID<input value={campaignId} onChange={e => setCampaignId(e.target.value)} placeholder="Link to marketing campaign" /></label>
      <label>Creative URL<input value={creativeUrl} onChange={e => setCreativeUrl(e.target.value)} placeholder="https://…" /></label>
      <label>External post/page URL<input value={externalLink} onChange={e => setExternalLink(e.target.value)} placeholder="https://…" /></label>
      <label>Alt text<input value={altText} onChange={e => setAltText(e.target.value)} placeholder="Accessible visual description" /></label>
      <label>Notes<textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Publishing notes" /></label>
      <button className="primary-button" disabled={busy} onClick={() => void create()}>Create Draft</button>
    </div></section>
    <section className="module-card"><h3>Publishing Queue & Performance</h3><div className="form-grid"><label>Publishing date/time<input type="datetime-local" value={schedule} onChange={e => setSchedule(e.target.value)} aria-label="Publishing schedule" /></label></div>
      {posts.map(post => <div className="list-row" key={post.id}><div><strong>{post.post_title || post.post_id}</strong><small>{post.platform} · {post.status}</small><small>Scheduled: {post.post_date ? new Date(post.post_date).toLocaleString() : "Not scheduled"}</small><small>Content linked: {post.content_asset_id ? "Yes" : "No"} · Campaign linked: {post.campaign_id ? "Yes" : "No"}</small><small>Reach {post.reach} · Impressions {post.impressions} · Likes {post.likes} · Comments {post.comments} · Shares {post.shares} · Saves {post.saves} · Clicks {post.clicks} · Views {post.views}</small></div><span>{post.status}</span><div>
        {post.status === "draft" && <button className="secondary-button" onClick={() => void move(post, "ready")}>Mark Ready</button>}
        {post.status === "ready" && <><button className="secondary-button" onClick={() => void move(post, "draft")}>Return to Draft</button><button className="secondary-button" onClick={() => void move(post, "scheduled")}>Schedule</button></>}
        {post.status === "scheduled" && <button className="secondary-button" onClick={() => void move(post, "ready")}>Unschedule</button>}
        {post.status === "scheduled" && <button className="secondary-button" onClick={() => void move(post, "published")}>Confirm Published</button>}
        {post.status === "published" && <button className="secondary-button" onClick={() => openMetrics(post)}>Edit Performance Metrics</button>}
      </div></div>)}
    </section></div>
    {metricPost && <section className="module-card"><h3>Record Performance — {metricPost.post_title || metricPost.post_id}</h3><p>Enter the actual values from the social platform. Values replace the existing snapshot for this post.</p><div className="form-grid">{Object.keys(emptyMetrics).map(key => <label key={key}>{key.charAt(0).toUpperCase() + key.slice(1)}<input type="number" min="0" value={metrics[key as keyof typeof metrics]} onChange={e => setMetrics(prev => ({ ...prev, [key]: Math.max(0, Number(e.target.value)) }))} /></label>)}<button className="primary-button" disabled={busy} onClick={() => void saveMetrics()}>Save Performance</button><button className="secondary-button" onClick={() => setMetricPost(null)}>Cancel</button></div></section>}
  </section>;
}
