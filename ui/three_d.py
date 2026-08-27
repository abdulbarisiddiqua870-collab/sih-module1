"""
3D / cinematic visual components for the Dashboard.

These render real interactive 3D graphics (WebGL via Three.js) and
canvas-based ambient animation inside Streamlit using
components.v1.html. They are purely presentational — none of them
touch inspection data logic; they only take already-computed values
(score, counts, status, labels) as plain arguments.
"""

import json

import streamlit.components.v1 as components

import config

_STATUS_HEX = {
    config.STATUS_PASS: "0x1E8E5A",
    config.STATUS_REVIEW: "0xC77700",
    config.STATUS_HIGH_PRIORITY: "0xC0392B",
}


def cinematic_hero(title: str, subtitle: str, badge_text: str = "", height: int = 150):
    """
    A cinematic hero banner: a drifting particle network on an animated
    dark gradient, a slow light sweep, and the title/subtitle fading
    and sliding into place on load.
    """
    badge_html = (
        f'<div class="hero-badge">{badge_text}</div>' if badge_text else ""
    )

    html = f"""
    <style>
      @keyframes hero-gradient {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
      }}
      @keyframes hero-fade-up {{
        from {{ opacity: 0; transform: translateY(14px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
      @keyframes hero-sweep {{
        0%   {{ transform: translateX(-120%) skewX(-18deg); }}
        100% {{ transform: translateX(220%) skewX(-18deg); }}
      }}
      @keyframes hero-pulse {{
        0%, 100% {{ opacity: 0.55; }}
        50% {{ opacity: 1; }}
      }}
      #hero-wrap {{
        position: relative; width: 100%; height: {height}px;
        border-radius: 18px; overflow: hidden;
        background: linear-gradient(120deg, #0a1626, #10233f 45%, #1B3A6B 100%);
        background-size: 220% 220%;
        animation: hero-gradient 14s ease infinite;
        box-shadow: 0 14px 34px rgba(10,22,38,0.4);
      }}
      #hero-canvas {{ position:absolute; inset:0; width:100%; height:100%; }}
      .hero-sweep-el {{
        position:absolute; top:0; left:0; width:35%; height:200%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07), transparent);
        animation: hero-sweep 6s ease-in-out infinite;
        pointer-events:none;
      }}
      .hero-content {{
        position:relative; z-index:2; height:100%;
        display:flex; flex-direction:column; justify-content:center;
        padding: 0 30px; color:white; font-family:-apple-system,Segoe UI,Roboto,sans-serif;
      }}
      .hero-title {{
        margin:0; font-size:1.9rem; font-weight:800; letter-spacing:0.01em;
        animation: hero-fade-up 0.7s ease-out both;
      }}
      .hero-sub {{
        margin:6px 0 0 0; color:#b9c8de; font-size:0.92rem;
        animation: hero-fade-up 0.7s ease-out 0.15s both;
      }}
      .hero-badge {{
        position:absolute; top:18px; right:24px; z-index:3;
        padding:4px 12px; border-radius:999px; font-weight:700; font-size:0.72rem;
        letter-spacing:0.05em; color:#7A5A00; background:#FFF3CD; border:1px solid #F5D98B;
        animation: hero-fade-up 0.7s ease-out 0.3s both, hero-pulse 2.4s ease-in-out infinite;
      }}
    </style>
    <div id="hero-wrap">
      <canvas id="hero-canvas"></canvas>
      <div class="hero-sweep-el"></div>
      {badge_html}
      <div class="hero-content">
        <h1 class="hero-title">{title}</h1>
        <p class="hero-sub">{subtitle}</p>
      </div>
    </div>
    <script>
      (function() {{
        const wrap = document.getElementById('hero-wrap');
        const canvas = document.getElementById('hero-canvas');
        const ctx = canvas.getContext('2d');
        let w, h, dpr;

        function size() {{
          dpr = Math.min(window.devicePixelRatio || 1, 2);
          w = wrap.clientWidth; h = wrap.clientHeight;
          canvas.width = w * dpr; canvas.height = h * dpr;
          canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }}
        size();
        window.addEventListener('resize', size);

        const N = 46;
        const pts = [];
        for (let i = 0; i < N; i++) {{
          pts.push({{
            x: Math.random() * w, y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
            r: Math.random() * 1.4 + 0.6,
          }});
        }}

        function step() {{
          ctx.clearRect(0, 0, w, h);
          for (const p of pts) {{
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0 || p.x > w) p.vx *= -1;
            if (p.y < 0 || p.y > h) p.vy *= -1;
          }}
          for (let i = 0; i < N; i++) {{
            for (let j = i + 1; j < N; j++) {{
              const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
              const dist = Math.sqrt(dx * dx + dy * dy);
              if (dist < 120) {{
                ctx.strokeStyle = 'rgba(143,179,255,' + (0.14 * (1 - dist / 120)) + ')';
                ctx.lineWidth = 0.6;
                ctx.beginPath();
                ctx.moveTo(pts[i].x, pts[i].y);
                ctx.lineTo(pts[j].x, pts[j].y);
                ctx.stroke();
              }}
            }}
          }}
          for (const p of pts) {{
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(180,205,255,0.55)';
            ctx.fill();
          }}
          requestAnimationFrame(step);
        }}
        step();
      }})();
    </script>
    """
    components.html(html, height=height + 10, scrolling=False)


def compliance_orb(score, status, height: int = 300):
    """
    A cinematic rotating 3D compliance orb: glowing wireframe
    icosahedron, two tilted orbiting rings, an additive-blended glow
    sprite behind it for a bloom-like effect, a starfield, a slow
    breathing pulse, and gentle mouse-parallax camera drift. Color
    reflects the dominant status; the center label counts up to the
    average compliance score.
    """
    color_hex = _STATUS_HEX.get(status, "0x555555")
    status_label = status or "REVIEW"

    html = f"""
    <div id="orb-wrap" style="position:relative;width:100%;height:{height}px;
         border-radius:16px;overflow:hidden;
         background:radial-gradient(circle at 50% 30%, #10233f 0%, #0a1626 70%);">
      <canvas id="orb-canvas" style="display:block;width:100%;height:100%;"></canvas>
      <div style="position:absolute;top:0;left:0;width:100%;height:100%;
           display:flex;flex-direction:column;align-items:center;justify-content:center;
           pointer-events:none;font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
        <div id="orb-score" style="font-size:3.2rem;font-weight:800;color:#ffffff;
             text-shadow:0 0 22px rgba(255,255,255,0.45);">0</div>
        <div style="font-size:0.85rem;letter-spacing:0.12em;color:#9fb4d1;margin-top:-6px;">
          COMPLIANCE SCORE
        </div>
        <div id="orb-status" style="margin-top:10px;padding:4px 14px;border-radius:999px;font-weight:700;
             font-size:0.78rem;letter-spacing:0.04em;color:white;
             background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.25);
             backdrop-filter:blur(4px);">
          {status_label}
        </div>
      </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
      (function() {{
        const wrap = document.getElementById('orb-wrap');
        const canvas = document.getElementById('orb-canvas');
        const targetScore = {json.dumps(score if score is not None else 0)};
        const scoreEl = document.getElementById('orb-score');
        const statusEl = document.getElementById('orb-status');

        function boot() {{
          if (typeof THREE === 'undefined') {{ setTimeout(boot, 50); return; }}

          const width = wrap.clientWidth;
          const height = wrap.clientHeight;

          const scene = new THREE.Scene();
          const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
          camera.position.z = 5.4;

          const renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true, alpha: true }});
          renderer.setSize(width, height);
          renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

          const color = new THREE.Color({color_hex});
          const group = new THREE.Group();
          scene.add(group);

          // glow sprite (soft radial gradient) behind the orb -> bloom-like effect
          const glowCanvas = document.createElement('canvas');
          glowCanvas.width = 256; glowCanvas.height = 256;
          const gctx = glowCanvas.getContext('2d');
          const grad = gctx.createRadialGradient(128, 128, 0, 128, 128, 128);
          grad.addColorStop(0, 'rgba(255,255,255,0.9)');
          grad.addColorStop(0.25, '#' + color.getHexString());
          grad.addColorStop(1, 'rgba(0,0,0,0)');
          gctx.fillStyle = grad;
          gctx.fillRect(0, 0, 256, 256);
          const glowTex = new THREE.CanvasTexture(glowCanvas);
          const glowMat = new THREE.SpriteMaterial({{ map: glowTex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }});
          const glowSprite = new THREE.Sprite(glowMat);
          glowSprite.scale.set(6.5, 6.5, 1);
          group.add(glowSprite);

          const geo = new THREE.IcosahedronGeometry(1.7, 1);
          const wireMat = new THREE.MeshBasicMaterial({{ color: color, wireframe: true, transparent: true, opacity: 0.95 }});
          const solidMat = new THREE.MeshPhongMaterial({{ color: color, transparent: true, opacity: 0.14, shininess: 90 }});
          const wireMesh = new THREE.Mesh(geo, wireMat);
          const solidMesh = new THREE.Mesh(geo, solidMat);
          group.add(solidMesh);
          group.add(wireMesh);

          // orbiting rings
          const ringGeo1 = new THREE.TorusGeometry(2.4, 0.012, 8, 120);
          const ringMat1 = new THREE.MeshBasicMaterial({{ color: color, transparent: true, opacity: 0.55 }});
          const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
          ring1.rotation.x = Math.PI / 2.4;
          group.add(ring1);

          const ringGeo2 = new THREE.TorusGeometry(2.9, 0.008, 8, 120);
          const ringMat2 = new THREE.MeshBasicMaterial({{ color: 0xffffff, transparent: true, opacity: 0.25 }});
          const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
          ring2.rotation.x = Math.PI / 1.7;
          ring2.rotation.y = Math.PI / 5;
          group.add(ring2);

          const light1 = new THREE.PointLight(0xffffff, 1.2);
          light1.position.set(4, 4, 6);
          scene.add(light1);
          scene.add(new THREE.AmbientLight(0x404060, 1.2));

          // starfield particles
          const starGeo = new THREE.BufferGeometry();
          const starCount = 220;
          const positions = new Float32Array(starCount * 3);
          for (let i = 0; i < starCount * 3; i++) {{
            positions[i] = (Math.random() - 0.5) * 16;
          }}
          starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
          const starMat = new THREE.PointsMaterial({{ color: 0x8fb3ff, size: 0.022, transparent: true, opacity: 0.65 }});
          const stars = new THREE.Points(starGeo, starMat);
          scene.add(stars);

          // gentle mouse parallax
          let targetRotX = 0, targetRotY = 0;
          wrap.addEventListener('mousemove', function(e) {{
            const rect = wrap.getBoundingClientRect();
            const nx = (e.clientX - rect.left) / rect.width - 0.5;
            const ny = (e.clientY - rect.top) / rect.height - 0.5;
            targetRotY = nx * 0.5;
            targetRotX = -ny * 0.3;
          }});

          let t = 0;
          function animate() {{
            t += 0.016;
            wireMesh.rotation.y += 0.004;
            wireMesh.rotation.x += 0.0015;
            solidMesh.rotation.y += 0.004;
            solidMesh.rotation.x += 0.0015;
            ring1.rotation.z += 0.006;
            ring2.rotation.z -= 0.004;
            stars.rotation.y += 0.0006;

            const pulse = 1 + Math.sin(t * 1.4) * 0.035;
            solidMesh.scale.set(pulse, pulse, pulse);
            wireMesh.scale.set(pulse, pulse, pulse);
            glowSprite.material.opacity = 0.75 + Math.sin(t * 1.4) * 0.15;

            group.rotation.y += (targetRotY - group.rotation.y) * 0.04;
            group.rotation.x += (targetRotX - group.rotation.x) * 0.04;

            renderer.render(scene, camera);
            requestAnimationFrame(animate);
          }}
          animate();

          let current = 0;
          const step = Math.max(1, Math.round(targetScore / 45));
          const counter = setInterval(function() {{
            current += step;
            if (current >= targetScore) {{ current = targetScore; clearInterval(counter); }}
            scoreEl.textContent = current;
          }}, 18);

          window.addEventListener('resize', function() {{
            const w = wrap.clientWidth, h = wrap.clientHeight;
            renderer.setSize(w, h);
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
          }});
        }}
        boot();
      }})();
    </script>
    """
    components.html(html, height=height + 10, scrolling=False)


def tilt_kpi_cards(cards: list, height: int = 150):
    """
    A row of glassmorphic KPI cards with a staggered entrance animation,
    a subtle real-time 3D tilt (CSS 3D transform following the cursor),
    and a soft glowing pulse ring on the accent border. `cards` is a
    list of dicts: {"label": str, "value": str, "accent": "#RRGGBB"}.
    """
    card_html = ""
    for i, c in enumerate(cards):
        accent = c.get("accent", "#1B3A6B")
        delay = 0.08 * i
        card_html += f"""
        <div class="tilt-card" style="--accent:{accent}; animation-delay:{delay}s;">
          <div class="tilt-card-inner">
            <div class="tilt-glow"></div>
            <div class="tilt-label">{c['label']}</div>
            <div class="tilt-value" style="color:{accent};">{c['value']}</div>
          </div>
        </div>
        """

    html = f"""
    <style>
      @keyframes tilt-in {{
        from {{ opacity:0; transform:translateY(16px) scale(0.96); }}
        to   {{ opacity:1; transform:translateY(0) scale(1); }}
      }}
      @keyframes tilt-glow-pulse {{
        0%, 100% {{ box-shadow: 0 0 0 0 rgba(255,255,255,0); }}
        50% {{ box-shadow: 0 0 16px 1px var(--accent); }}
      }}
      .tilt-row {{
        display:flex; gap:14px; flex-wrap:wrap; font-family:-apple-system,Segoe UI,Roboto,sans-serif;
      }}
      .tilt-card {{
        flex:1; min-width:150px; perspective:600px;
        animation: tilt-in 0.55s cubic-bezier(.2,.8,.2,1) both;
      }}
      .tilt-card-inner {{
        position:relative; overflow:hidden;
        background:linear-gradient(145deg, rgba(255,255,255,0.9), rgba(245,247,250,0.75));
        border:1px solid rgba(27,58,107,0.12);
        border-radius:14px; padding:16px 18px;
        box-shadow:0 6px 18px rgba(16,24,40,0.08), inset 0 0 0 1px rgba(255,255,255,0.4);
        transform-style:preserve-3d;
        transition:transform 0.12s ease-out, box-shadow 0.2s ease-out;
        border-top:3px solid var(--accent);
        will-change:transform;
        animation: tilt-glow-pulse 3.2s ease-in-out infinite;
      }}
      .tilt-card-inner:hover {{
        box-shadow:0 14px 30px rgba(16,24,40,0.16);
      }}
      .tilt-glow {{
        position:absolute; top:-40%; left:-20%; width:60%; height:180%;
        background:linear-gradient(120deg, transparent, rgba(255,255,255,0.35), transparent);
        transform:rotate(20deg);
        animation: tilt-sheen 4.5s ease-in-out infinite;
        pointer-events:none;
      }}
      @keyframes tilt-sheen {{
        0%   {{ left:-40%; }}
        50%  {{ left:120%; }}
        100% {{ left:120%; }}
      }}
      .tilt-label {{
        font-size:0.78rem; color:#6B7280; letter-spacing:0.03em; margin-bottom:6px;
        text-transform:uppercase;
      }}
      .tilt-value {{
        font-size:1.9rem; font-weight:800; line-height:1;
      }}
    </style>
    <div class="tilt-row" id="tilt-row">
      {card_html}
    </div>
    <script>
      (function() {{
        const cards = document.querySelectorAll('#tilt-row .tilt-card-inner');
        cards.forEach(function(card) {{
          card.addEventListener('mousemove', function(e) {{
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const cx = rect.width / 2, cy = rect.height / 2;
            const rotY = ((x - cx) / cx) * 8;
            const rotX = -((y - cy) / cy) * 8;
            card.style.transform = `rotateX(${{rotX}}deg) rotateY(${{rotY}}deg) translateZ(4px)`;
          }});
          card.addEventListener('mouseleave', function() {{
            card.style.transform = 'rotateX(0deg) rotateY(0deg) translateZ(0)';
          }});
        }});
      }})();
    </script>
    """
    components.html(html, height=height, scrolling=False)
