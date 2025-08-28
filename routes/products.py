from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from core.config import get_db_config
import pymysql
from core.utils import log_error, log_info
from core.forms import ProductForm

bp = Blueprint('products', __name__, url_prefix='/products')


def get_db_connection():
    try:
        cfg = get_db_config()
        return pymysql.connect(**cfg)
    except Exception as e:
        log_error(f"Erreur DB products: {e}")
        return None


@bp.route('/')
def index():
    products = []
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT id, sku, name, price, stock, description FROM products ORDER BY name")
                products = cur.fetchall()
        except Exception as e:
            # try create table if missing
            try:
                if hasattr(e, 'args') and e.args and isinstance(e.args[0], int) and e.args[0] == 1146:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS products (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                sku VARCHAR(100) DEFAULT NULL,
                                name VARCHAR(255) NOT NULL,
                                price DECIMAL(10,2) DEFAULT NULL,
                                stock INT DEFAULT NULL,
                                description TEXT,
                                created_by_user_id INT DEFAULT NULL,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                        """)
                        conn.commit()
                    # retry select
                    with conn.cursor(pymysql.cursors.DictCursor) as cur:
                        cur.execute("SELECT id, sku, name, price, stock, description FROM products ORDER BY name")
                        products = cur.fetchall()
                else:
                    log_error(f"Erreur récupération produits: {e}")
            except Exception as e2:
                log_error(f"Erreur récupération produits (retry): {e2}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return render_template('products/index.html', products=products)


@bp.route('/add', methods=['GET', 'POST'])
def add():
    form = ProductForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            sku = form.sku.data
            name = form.name.data
            price = form.price.data
            stock = form.stock.data
            description = form.description.data
        else:
            flash('Veuillez corriger les erreurs du formulaire', 'error')
            return render_template('products/add.html', form=form)
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return render_template('products/add.html')
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO products (sku, name, price, stock, description, created_by_user_id, created_at) VALUES (%s,%s,%s,%s,%s,%s,NOW())",
                            (sku, name, price, stock, description, session.get('user_id')))
                conn.commit()
                flash('Produit ajouté', 'success')
                return redirect(url_for('products.index'))
        except Exception as e:
            # try create table if missing
            try:
                if hasattr(e, 'args') and e.args and isinstance(e.args[0], int) and e.args[0] == 1146:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS products (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                sku VARCHAR(100) DEFAULT NULL,
                                name VARCHAR(255) NOT NULL,
                                price DECIMAL(10,2) DEFAULT NULL,
                                stock INT DEFAULT NULL,
                                description TEXT,
                                created_by_user_id INT DEFAULT NULL,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                        """)
                        conn.commit()
                    # retry insert
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO products (sku, name, price, stock, description, created_by_user_id, created_at) VALUES (%s,%s,%s,%s,%s,%s,NOW())",
                                    (sku, name, price, stock, description, session.get('user_id')))
                        conn.commit()
                        flash('Produit ajouté', 'success')
                        return redirect(url_for('products.index'))
            except Exception as e2:
                log_error(f"Erreur ajout produit (retry): {e2}")
            log_error(f"Erreur ajout produit: {e}")
            flash('Erreur lors de l\'ajout du produit', 'error')
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return render_template('products/add.html', form=form)


@bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
def edit(product_id):
    conn = get_db_connection()
    form = ProductForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            sku = form.sku.data
            name = form.name.data
            price = form.price.data
            stock = form.stock.data
            description = form.description.data
        else:
            flash('Veuillez corriger les erreurs du formulaire', 'error')
            return render_template('products/edit.html', form=form, product={'id': product_id})
        if not conn:
            flash('Erreur DB', 'error')
            return redirect(url_for('products.index'))
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE products SET sku=%s, name=%s, price=%s, stock=%s, description=%s WHERE id=%s",
                            (sku, name, price, stock, description, product_id))
                conn.commit()
                flash('Produit mis à jour', 'success')
                return redirect(url_for('products.view', product_id=product_id))
        except Exception as e:
            log_error(f"Erreur update produit: {e}")
            flash('Erreur lors de la mise à jour', 'error')
        finally:
            try:
                conn.close()
            except Exception:
                pass

    product = None
    if conn:
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT id, sku, name, price, stock, description FROM products WHERE id = %s", (product_id,))
                product = cur.fetchone()
        except Exception as e:
            log_error(f"Erreur lecture produit: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    if not product:
        flash('Produit introuvable', 'error')
        return redirect(url_for('products.index'))
    # populate form with existing values
    form.sku.data = product.get('sku')
    form.name.data = product.get('name')
    form.price.data = product.get('price')
    form.stock.data = product.get('stock')
    form.description.data = product.get('description')
    return render_template('products/edit.html', product=product, form=form)


@bp.route('/<int:product_id>/delete', methods=['POST'])
def delete(product_id):
    conn = get_db_connection()
    if not conn:
        flash('Erreur DB', 'error')
        return redirect(url_for('products.index'))
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            flash('Produit supprimé', 'success')
    except Exception as e:
        log_error(f"Erreur suppression produit: {e}")
        flash('Erreur lors de la suppression', 'error')
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return redirect(url_for('products.index'))


@bp.route('/<int:product_id>')
def view(product_id):
    product = None
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT id, sku, name, price, stock, description FROM products WHERE id = %s", (product_id,))
                product = cur.fetchone()
        except Exception as e:
            log_error(f"Erreur lecture produit: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    if not product:
        flash('Produit introuvable', 'error')
        return redirect(url_for('products.index'))
    return render_template('products/view.html', product=product)


@bp.route('/api/list')
def api_list():
    """Return JSON list of products for select boxes."""
    q = request.args.get('q')
    limit = int(request.args.get('limit') or 50)
    products = []
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                if q:
                    cur.execute("SELECT id, sku, name, price FROM products WHERE name LIKE %s OR sku LIKE %s LIMIT %s", (f"%{q}%", f"%{q}%", limit))
                else:
                    cur.execute("SELECT id, sku, name, price FROM products ORDER BY name LIMIT %s", (limit,))
                products = cur.fetchall()
        except Exception as e:
            log_error(f"Erreur API products list: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return jsonify(products)
