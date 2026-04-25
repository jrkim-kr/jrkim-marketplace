import puppeteer from 'puppeteer';
import fs from 'fs';

// --- Config ---
const configPath = process.argv[2];
if (!configPath) {
  console.error('Usage: node capture.mjs <config.json>');
  process.exit(1);
}

const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
const {
  baseUrl,
  outputDir,
  viewport = { width: 1440, height: 900 },
  ignoreHTTPSErrors = true,
  publicPages = [],
  auth,
  authenticatedPages = [],
} = config;

// Warn if output directory already has files
if (fs.existsSync(outputDir)) {
  const existing = fs.readdirSync(outputDir).filter(f => f !== '.DS_Store');
  if (existing.length > 0) {
    console.log(`⚠️  Output directory already exists with ${existing.length} items — files may be overwritten.\n`);
  }
}

// Ensure output directories (only create what's needed)
if (publicPages.length > 0) {
  fs.mkdirSync(`${outputDir}/public`, { recursive: true });
}
if (authenticatedPages.length > 0) {
  fs.mkdirSync(`${outputDir}/authenticated`, { recursive: true });
}

const results = [];

// Dedup is scoped per auth context — public and authenticated are independent
// because the same URL can show different content before/after login
const capturedUrlsByContext = { public: new Set(), authenticated: new Set() };

// Normalize path+query for order-insensitive matching (e.g., ?tab=sync&view=list == ?view=list&tab=sync)
function normalizePath(p) {
  try {
    const url = new URL(p, 'http://localhost');
    url.searchParams.sort();
    return url.pathname + url.search;
  } catch {
    return p;
  }
}

const configuredPathsByContext = {
  public: new Set(publicPages.map(p => normalizePath(p.path))),
  authenticated: new Set(authenticatedPages.map(p => normalizePath(p.path))),
};

async function screenshot(page, name, url, waitFor, subdir) {
  const dir = `${outputDir}/${subdir}`;
  const contextUrls = capturedUrlsByContext[subdir];
  const contextPaths = configuredPathsByContext[subdir];

  console.log(`📸 ${name} → ${url}`);
  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, waitFor || 2000));
    const finalUrl = page.url();
    const finalPath = normalizePath(new URL(finalUrl).pathname + new URL(finalUrl).search);

    // Skip only if redirected to a duplicate within the SAME auth context
    if (finalUrl !== url && contextUrls.has(finalUrl)) {
      console.log(`   ↪ Redirected to: ${finalUrl}`);
      console.log(`   ⏭️  Skipped (duplicate — already captured in ${subdir})`);
      results.push({ name, path: null, url, finalUrl, success: true, skipped: true, reason: 'redirect-duplicate' });
      return;
    }

    // Skip only if redirected to another page configured in the SAME context
    if (finalUrl !== url && contextPaths.has(finalPath)) {
      console.log(`   ↪ Redirected to: ${finalUrl}`);
      console.log(`   ⏭️  Skipped (will be captured as a separate ${subdir} page)`);
      results.push({ name, path: null, url, finalUrl, success: true, skipped: true, reason: 'redirect-to-configured-page' });
      return;
    }

    await page.screenshot({ path: `${dir}/${name}.png`, fullPage: true });
    contextUrls.add(finalUrl);
    if (finalUrl !== url) {
      console.log(`   ↪ Redirected to: ${finalUrl}`);
    }
    console.log(`   ✅ Saved: ${subdir}/${name}.png`);
    results.push({ name, path: `${subdir}/${name}.png`, url, finalUrl, success: true, skipped: false });
  } catch (err) {
    console.error(`   ❌ ${err.message}`);
    results.push({ name, url, success: false, error: err.message });
  }
}

async function main() {
  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--ignore-certificate-errors',
      '--ignore-certificate-errors-spki-list',
    ],
    ignoreHTTPSErrors,
  });

  // --- Public Pages ---
  if (publicPages.length > 0) {
    console.log('\n📄 Capturing public pages...\n');
    const page = await browser.newPage();
    await page.setViewport(viewport);
    for (const p of publicPages) {
      await screenshot(page, p.name, `${baseUrl}${p.path}`, p.waitFor, 'public');
    }
    await page.close();
  }

  // --- Authenticated Pages ---
  if (auth && authenticatedPages.length > 0) {
    console.log('\n🔐 Logging in...\n');
    const page = await browser.newPage();
    await page.setViewport(viewport);

    // Navigate to login page
    await page.goto(`${baseUrl}${auth.loginUrl}`, {
      waitUntil: 'networkidle2',
      timeout: 30000,
    });
    await new Promise(r => setTimeout(r, auth.waitBeforeLogin || 2000));

    // Find and fill login form
    const usernameInput = await page.$(auth.usernameSelector);
    const passwordInput = await page.$(auth.passwordSelector);

    let loginSuccess = false;

    if (!usernameInput || !passwordInput) {
      console.error('❌ Could not find login form inputs');
      console.error(`   Username selector: ${auth.usernameSelector}`);
      console.error(`   Password selector: ${auth.passwordSelector}`);
    } else {
      await usernameInput.type(auth.username);
      await passwordInput.type(auth.password);

      const submitBtn = await page.$(auth.submitSelector);
      if (submitBtn) {
        await submitBtn.click();
        await new Promise(r => setTimeout(r, auth.waitAfterLogin || 6000));
      } else {
        console.error('❌ Could not find submit button');
        console.error(`   Submit selector: ${auth.submitSelector}`);
      }

      const currentUrl = page.url();
      if (auth.successIndicator && currentUrl.includes(auth.successIndicator)) {
        console.log(`✅ Login successful → ${currentUrl}\n`);
        loginSuccess = true;
      } else if (auth.successIndicator) {
        console.log(`⚠️  Login failed. URL: ${currentUrl} (expected to contain: ${auth.successIndicator})\n`);
      } else {
        console.log(`   Login complete → ${currentUrl}\n`);
        loginSuccess = true;
      }
    }

    if (!loginSuccess) {
      console.error('❌ Skipping authenticated pages — login failed.\n');
      results.push(...authenticatedPages.map(p => ({
        name: p.name, url: `${baseUrl}${p.path}`, success: false, error: 'login-failed',
      })));
    } else {
      console.log('📄 Capturing authenticated pages...\n');
      for (const p of authenticatedPages) {
        await screenshot(page, p.name, `${baseUrl}${p.path}`, p.waitFor, 'authenticated');
      }
    }
    await page.close();
  }

  await browser.close();

  // --- Manifest ---
  const manifest = {
    capturedAt: new Date().toISOString(),
    baseUrl,
    viewport,
    total: results.length,
    success: results.filter(r => r.success).length,
    failed: results.filter(r => !r.success).length,
    screenshots: results,
  };
  fs.writeFileSync(`${outputDir}/manifest.json`, JSON.stringify(manifest, null, 2));

  // --- Summary ---
  const saved = results.filter(r => r.success && !r.skipped).length;
  const skipped = results.filter(r => r.skipped).length;
  const fail = results.filter(r => !r.success).length;
  console.log(`\n${'='.repeat(50)}`);
  console.log(`✅ ${saved} screenshots captured${skipped > 0 ? `, ⏭️  ${skipped} skipped (redirects)` : ''}${fail > 0 ? `, ❌ ${fail} failed` : ''}`);
  console.log(`📁 Saved to: ${outputDir}`);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
