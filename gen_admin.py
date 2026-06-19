import os

TEMPLATE = r"""{% extends "base.html" %}
{% block content %}

<!-- Admin header -->
<div style="background:var(--surface);border-bottom:0.5px solid var(--border);padding:0 1.5rem;">
  <div style="max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;height:48px;">
    <span style="font-weight:600;font-size:15px;">&#9881;&#65039; {{ data.league_name }} &mdash; Admin</span>
    <a href="/admin/logout" class="btn-secondary" style="font-size:13px;text-decoration:none;padding:6px 14px;border:0.5px solid var(--border-med);border-radius:var(--radius);">Log out</a>
  </div>
</div>

<!-- Tab bar -->
<div class="tabs-bar">
  <button class="tab-btn active" data-tab="setup">Setup</button>
  <button class="tab-btn" data-tab="tiers">Tiers</button>
  <button class="tab-btn" data-tab="auction">Auction</button>
  <button class="tab-btn" data-tab="matches">Matches</button>
  <button class="tab-btn" data-tab="points">Points</button>
  <button class="tab-btn" data-tab="danger">Danger Zone</button>
</div>

<div class="container">
PLACEHOLDER_CONTENT
</div><!-- .container -->

PLACEHOLDER_SCRIPT
{% endblock %}
"""

print(TEMPLATE[:200])
