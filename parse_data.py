import itertools
import random

import snap


"""
These string match the beginning of lines in the data file. This is how we
know which object field to populate with the current line
"""
ASIN = 'ASIN:'
GROUP = 'group:'
ID = 'Id:'
REVIEW = 'reviews:'
SALESRANK = 'salesrank:'
SIMILAR = 'similar:'
TITLE = 'title:'


class Product(object):
    """
    Holds all of the information about a single product:

    asin - amazon product id_to_prod
    avg_rating - average product review (max. 5)
    categories - where this product fits in the amazon catalog
        (ex.Books[283155]|Subjects[1000]|Cooking, Food & Wine[6]|General[4233])
    downloaded_reviews - how many of the reviews made it into the dataset
    group - general category (eg. Books)
    id - id of the product in data file, will be used as the NodeID in networks
    reviews - dictionary of amazon user_id->review object, see below for
        description
    salesrank - amazon salesrank score
    similar - list of asin of similar products
    title - name of the product
    total_reviews - total number of reviews for the product
    """

    def __init__(self, asin=None, avg_rating=None, categories=list(),
                 downloaded_reviews=None, group=None, id=None, salesrank=None,
                 similar=list(), title=None, total_reviews=None):
        self.asin = asin
        self.avg_rating = avg_rating
        self.categories = categories
        self.downloaded_reviews = downloaded_reviews
        self.group = group
        self.id = id
        self.reviews = dict()
        self.salesrank = salesrank
        self.similar = similar
        self.title = title
        self.total_reviews = total_reviews

    def __repr__(self):
        return self.asin + ': ' + self.title


class Review(object):
    """
    Holds all of the information for a single review:

    date - formatted YEAR-MONTH-DAY that the review was published
    helpful - number of votes that found the review helpful
    rating - star rating of the product (range 1-5)
    votes - total votes on the review
    product_id - asin of the product that was reviewed
    """

    def __init__(self, date, rating, votes, helpful, prod_id):
        self.date = str(date)
        self.helpful = int(helpful)
        self.rating = int(rating)
        self.votes = int(votes)
        self.product_id = str(prod_id)

    def __repr__(self):
        return self.date + ': ' + str(self.rating)


def parse_file(filename):
    """
    Parses the data file into 3 dictionaries:
    1) asin_to_product <String asin, Product product>
    2) id_to_product <Int id, Product product>
        used to match the network NodeId to a product in the product graph
    3) user_to_id <String Amazon user id, Int NodeId>
        used to match an Amazon userId to the network NodeId in the user graph

    Product entries are delimited by a new line, so when reading in an empty
    line, enter the current object into the dictionary and reset
    current_product to a new Product object.
    """

    asin_to_product = dict()
    id_to_product = dict()
    user_to_node_id = dict()

    # keep track of the current object since we're reading one line at a time
    current_product = None
    count = 0
    user_count = 0

    with open(filename, 'r') as data_file:
        for line in data_file:
            line = line.strip(' ').split()
            if not line:    # empty line
                if current_product:
                    asin_to_product[current_product.asin] = current_product
                    id_to_product[current_product.id] = current_product
                    if count % 1000 == 0:
                        print 'processed', str(count), 'products'
                    count += 1
                current_product = Product()
                continue

            # fill in the fields of the Product object
            if line[0] == ID:
                current_product.id = int(line[1])
            elif line[0] == ASIN:
                current_product.asin = line[1]
            elif line[0] == TITLE:
                current_product.title = ' '.join(line[1:])
            elif line[0] == GROUP:
                current_product.group = line[1]
            elif line[0] == SALESRANK:
                current_product.salesrank = int(line[1])
            elif line[0] == SIMILAR and line[1] > 0:
                current_product.similar = line[2:]
            elif line[0].startswith('|'):
                current_product.categories.append(line)
            elif line[0] == REVIEW:
                current_product.total_reviews = int(line[2])
                current_product.downloaded_reviews = int(line[4])
                current_product.avg_rating = float(line[-1])
            elif line[0].startswith('1') or line[0].startswith('2'):
                # parses a single review object
                review = Review(line[0], line[4], line[6], line[-1],
                                current_product.asin)
                current_product.reviews[line[2]] = review
                if not user_to_node_id.get(line[2], None):
                    user_to_node_id[line[2]] = user_count
                    user_count += 1

    return asin_to_product, id_to_product, user_to_node_id


def make_product_graph(id_to_prod, asin_to_product):
    """
    Makes the product graph with nodes of product and edges linking similar
    products.
    """

    graph = snap.TUNGraph.New()

    # add all nodes to the graph
    for node_id in id_to_prod.iterkeys():
        graph.AddNode(node_id)

    # add edges between similar products
    for product in id_to_prod.itervalues():
        for similar_asin in product.similar:
            similar_product = asin_to_product.get(similar_asin, None)
            if similar_product:
                graph.AddEdge(product.id, similar_product.id)

    return graph


def count_user_co_reviews(id_to_prod):
    """
    Makes a dictionary of users who have reviewed the same product.
    (String Amazon UserID 1, String Amazon UserID 2) -> list of productIDs they
    have both reviewed.
    """

    user_co_reviews = dict()
    for product in id_to_prod.itervalues():
        for user_pair in itertools.combinations(product.reviews.keys(), 2):
            if not user_co_reviews.get(user_pair, None):
                user_co_reviews[user_pair] = list()
            user_co_reviews[user_pair].append(product.id)

    return user_co_reviews


def make_user_graph(user_to_id, user_co_reviews):
    """
    Makes the user graph with nodes of users and edges means that they reviewed
    at least one of the same products. The complete list of those products can
    be accessed in user_co_reviews. The edge weight is the number of products
    co-reviewed.
    """

    graph = snap.TUNGraph.New()

    # add all user nodes to the graph
    for user_id, node_id in user_to_id.iteritems():
        graph.AddNode(node_id)

    for user_pair in user_co_reviews.keys():
        graph.AddEdge(user_to_id[user_pair[0]], user_to_id[user_pair[1]])

    return graph


def main():
    filename = 'amazon-small.txt'
    asin_to_product, id_to_product, user_to_node_id = parse_file(filename)
    print 'data file processed'
    prod_graph = make_product_graph(id_to_product, asin_to_product)
    print 'product graph created'
    user_co_reviews = count_user_co_reviews(id_to_product)
    print 'user_co_reviews parsed'
    user_graph = make_user_graph(user_to_node_id, user_co_reviews)
    print 'user graph generated'

    # choose a random user and get recommended products for them, see how many
    # of the recommended products they already own
    for i in range(10):
        random_user_id = random.choice(user_to_node_id.keys())
        products_reviewed = list()
        for product in id_to_product.values():
            if random_user_id in product.reviews.keys():
                products_reviewed.append(product.id)

        random_asin = id_to_product[random.choice(products_reviewed)].asin
        similar_products = asin_to_product[random_asin].similar
        print 'randomly chosen product', asin_to_product[random_asin]

        print 'other products user reviewed', products_reviewed

        print 'similar products', similar_products

        print 'number of products in common', \
            set(products_reviewed).intersection(similar_products)



if __name__ == '__main__':
    main()