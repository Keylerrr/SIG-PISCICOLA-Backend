from django.db import models
from django.utils import timezone

DEPARTMENT_CITY_MAP = {
    'amazonas':           ['Leticia', 'Puerto Nariño'],
    'antioquia':          ['Medellín', 'Bello', 'Itagüí', 'Envigado', 'Rionegro', 'Apartadó', 'Turbo', 'Caucasia'],
    'arauca':             ['Arauca', 'Saravena', 'Tame'],
    'atlantico':          ['Barranquilla', 'Soledad', 'Malambo', 'Sabanalarga'],
    'bolivar':            ['Cartagena', 'Magangué', 'Mompox'],
    'boyaca':             ['Tunja', 'Sogamoso', 'Duitama', 'Chiquinquirá', 'Paipa'],
    'caldas':             ['Manizales', 'La Dorada', 'Riosucio', 'Chinchiná'],
    'caqueta':            ['Florencia', 'San Vicente del Caguán'],
    'casanare':           ['Yopal', 'Aguazul', 'Villanueva'],
    'cauca':              ['Popayán', 'Santander de Quilichao', 'Puerto Tejada'],
    'cesar':              ['Valledupar', 'Aguachica', 'Bosconia'],
    'choco':              ['Quibdó', 'Istmina'],
    'cordoba':            ['Montería', 'Lorica', 'Cereté', 'Sahagún'],
    'cundinamarca':       ['Bogotá', 'Soacha', 'Zipaquirá', 'Fusagasugá', 'Girardot', 'Facatativá', 'Chía', 'Mosquera'],
    'guainia':            ['Inírida'],
    'guaviare':           ['San José del Guaviare'],
    'huila':              ['Neiva', 'Pitalito', 'Garzón'],
    'la_guajira':         ['Riohacha', 'Maicao', 'Uribia'],
    'magdalena':          ['Santa Marta', 'Ciénaga', 'El Banco', 'Fundación'],
    'meta':               ['Villavicencio', 'Acacías', 'Granada'],
    'narino':             ['Pasto', 'Tumaco', 'Ipiales', 'Túquerres'],
    'norte_de_santander': ['Cúcuta', 'Ocaña', 'Pamplona', 'Villa del Rosario'],
    'putumayo':           ['Mocoa', 'Puerto Asís', 'Orito'],
    'quindio':            ['Armenia', 'Calarcá', 'Montenegro'],
    'risaralda':          ['Pereira', 'Dosquebradas', 'Santa Rosa de Cabal'],
    'san_andres':         ['San Andrés', 'Providencia'],
    'santander':          ['Bucaramanga', 'Floridablanca', 'Girón', 'Barrancabermeja', 'San Gil', 'Socorro'],
    'sucre':              ['Sincelejo', 'Corozal', 'San Marcos'],
    'tolima':             ['Ibagué', 'Espinal', 'Honda', 'Melgar'],
    'valle_del_cauca':    ['Cali', 'Buenaventura', 'Palmira', 'Tuluá', 'Buga', 'Cartago', 'Jamundí'],
    'vaupes':             ['Mitú'],
    'vichada':            ['Puerto Carreño'],
}

DEPARTMENT_LABELS = {
    'amazonas':           'Amazonas',
    'antioquia':          'Antioquia',
    'arauca':             'Arauca',
    'atlantico':          'Atlántico',
    'bolivar':            'Bolívar',
    'boyaca':             'Boyacá',
    'caldas':             'Caldas',
    'caqueta':            'Caquetá',
    'casanare':           'Casanare',
    'cauca':              'Cauca',
    'cesar':              'Cesar',
    'choco':              'Chocó',
    'cordoba':            'Córdoba',
    'cundinamarca':       'Cundinamarca',
    'guainia':            'Guainía',
    'guaviare':           'Guaviare',
    'huila':              'Huila',
    'la_guajira':         'La Guajira',
    'magdalena':          'Magdalena',
    'meta':               'Meta',
    'narino':             'Nariño',
    'norte_de_santander': 'Norte de Santander',
    'putumayo':           'Putumayo',
    'quindio':            'Quindío',
    'risaralda':          'Risaralda',
    'san_andres':         'San Andrés y Providencia',
    'santander':          'Santander',
    'sucre':              'Sucre',
    'tolima':             'Tolima',
    'valle_del_cauca':    'Valle del Cauca',
    'vaupes':             'Vaupés',
    'vichada':            'Vichada',
}
DEPARTMENT_CHOICES = [(key, label) for key, label in DEPARTMENT_LABELS.items()]
CITY_CHOICES = [(city, city) for cities in DEPARTMENT_CITY_MAP.values() for city in cities]

class Farm(models.Model):
    name = models.CharField(max_length=200)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    city = models.CharField(max_length=100, choices=CITY_CHOICES, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    total_area_ha = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    manager = models.ForeignKey("user.Manager", on_delete=models.SET_NULL, null=True, blank=True, related_name="farms")
    # is_active = models.BooleanField(default=True)
    # deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "farm"

    def __str__(self):
        return self.name

    # def soft_delete(self):
    #     self.deleted_at = timezone.now()
    #     self.save(update_fields=["deleted_at"])