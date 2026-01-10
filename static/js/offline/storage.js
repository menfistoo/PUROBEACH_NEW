/**
 * IndexedDB Storage for Offline Data
 * Handles map and reservation data persistence
 */

const DB_NAME = 'purobeach_offline';
const DB_VERSION = 1;

/**
 * Open or create the IndexedDB database
 * @returns {Promise<IDBDatabase>}
 */
export async function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            // Store for map data (zones, furniture, availability)
            if (!db.objectStoreNames.contains('map_data')) {
                db.createObjectStore('map_data', { keyPath: 'date' });
            }

            // Store for sync metadata
            if (!db.objectStoreNames.contains('sync_meta')) {
                db.createObjectStore('sync_meta', { keyPath: 'key' });
            }
        };
    });
}

/**
 * Save map data for a specific date
 * @param {string} date - Date string YYYY-MM-DD
 * @param {Object} data - Map data (zones, furniture, availability, reservations)
 * @returns {Promise<void>}
 */
export async function saveMapData(date, data) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('map_data', 'readwrite');
        const store = tx.objectStore('map_data');

        const record = {
            date,
            data,
            savedAt: new Date().toISOString()
        };

        const request = store.put(record);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();

        tx.oncomplete = () => db.close();
    });
}

/**
 * Get map data for a specific date
 * @param {string} date - Date string YYYY-MM-DD
 * @returns {Promise<Object|null>}
 */
export async function getMapData(date) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('map_data', 'readonly');
        const store = tx.objectStore('map_data');

        const request = store.get(date);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result || null);

        tx.oncomplete = () => db.close();
    });
}

/**
 * Save sync metadata
 * @param {Object} meta - Sync metadata
 * @returns {Promise<void>}
 */
export async function saveSyncMeta(meta) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('sync_meta', 'readwrite');
        const store = tx.objectStore('sync_meta');

        const record = { key: 'current', ...meta };
        const request = store.put(record);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();

        tx.oncomplete = () => db.close();
    });
}

/**
 * Get sync metadata
 * @returns {Promise<Object|null>}
 */
export async function getSyncMeta() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('sync_meta', 'readonly');
        const store = tx.objectStore('sync_meta');

        const request = store.get('current');
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result || null);

        tx.oncomplete = () => db.close();
    });
}

/**
 * Clear old data (dates other than today)
 * @param {string} todayDate - Today's date YYYY-MM-DD
 * @returns {Promise<void>}
 */
export async function clearOldData(todayDate) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('map_data', 'readwrite');
        const store = tx.objectStore('map_data');

        const request = store.openCursor();
        request.onerror = () => reject(request.error);

        request.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor) {
                if (cursor.key !== todayDate) {
                    cursor.delete();
                }
                cursor.continue();
            }
        };

        tx.oncomplete = () => {
            db.close();
            resolve();
        };
    });
}
